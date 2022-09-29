#################################################################################
# DISPATCHES was produced under the DOE Design Integration and Synthesis
# Platform to Advance Tightly Coupled Hybrid Energy Systems program (DISPATCHES),
# and is copyright (c) 2021 by the software owners: The Regents of the University
# of California, through Lawrence Berkeley National Laboratory, National
# Technology & Engineering Solutions of Sandia, LLC, Alliance for Sustainable
# Energy, LLC, Battelle Energy Alliance, LLC, University of Notre Dame du Lac, et
# al. All rights reserved.
#
# Please see the files COPYRIGHT.md and LICENSE.md for full copyright and license
# information, respectively. Both files are also available online at the URL:
# "https://github.com/gmlc-dispatches/dispatches".
#################################################################################

import pandas as pd
import numpy as np
from tslearn.utils import to_time_series_dataset
from tslearn.clustering import TimeSeriesKMeans
import matplotlib.pyplot as plt
import os
import re

'''
This code only do clustering on dispacth power profiles.

Set two clusters: capacity factor = 0 or 1. Filter out 0/1 capacity days before do clustering when filter_opt = True.
'''

class TSA64K:
    def __init__(self, years, num_clusters, filter_opt = True, metric = 'euclidean'):
        '''
        Initializes the bidder object.

        Arguments:
            dispatch_data: csv files with the dispatch power data

            metric: distance metric (“euclidean” or “dtw”).

            years: The size for the clustering dataset.

            filter: If we need to filter 0/1 capacity days

        Return:
            None
        '''
        # self.dispatch_data = dispatch_data
        self.metric = metric 
        self.years = years
        self.num_clusters = num_clusters
        self.filter = filter_opt


    # @property
    # def dispatch_data(self):

    #     '''
    #     Porperty getter of dispatch_data

    #     Returns:
    #         np array
    #     '''
    #     return self._dispatch_data


    # @dispatch_data.setter
    # def dispatch_data(self, value):

    #     '''
    #     Property setter for dispatch_data

    #     Returns:
    #         None
    #     '''
        
    #     if not isinstance(value, np.ndarray):
    #         raise TypeError(
    #             f"The dispatch data must be numpy.ndarray, but {type(value)} is provided"
    #         )

    #     self._dispatch_data = value

    @property
    def metric(self):

        '''
        Porperty getter of metric

        Returns:
            metric
        '''

        return self._metric

    @metric.setter
    def metric(self, value):

        '''
        Property setter for metric

        Returns:
            None
        '''

        if not (value == 'euclidean' or value == 'dtw'): 
            raise ValueError(
                f"The metric must be one of euclidean or dtw, but {value} is provided"
            )
        
        self._metric = value

    @property
    def years(self):

        '''
        Porperty getter of years

        Returns:
            int: number of years for clustering
        '''

        return self._years


    @years.setter
    def years(self, value):
        
        '''
        Property setter of years

        Returns:
            None
        '''

        if not isinstance(value, int):
            raise TypeError(
                f"The number of clustering years must be integer, but {type(value)} is given."
            )
        self._years = value


    @property
    def num_clusters(self):

        '''
        Property getter of num_clusters

        Returns:
            int: number of clusters for the clustering
            (k-means need given number of clusters)
        '''

        return self._num_clusters

    
    @num_clusters.setter
    def num_clusters(self, value):

        '''
        Property setter of num_clusters

        Returns:
            None
        '''

        if not isinstance(value, int):
            raise TypeError(
                f"Number of clusters must be integer, but {type(value)} is given"
            )

        self._num_clusters = value


    @property
    def filter_opt(self):
    
        '''
        Property getter of filter_opt

        Return:
            bool: if want filter 0/1 days in clustering
        '''
        return self._filter_opt


    @filter_opt.setter
    def filter_opt(self, value):

        '''
        Property setter of filter_opt

        Returns:
            None
        '''

        if not isinstance(value, bool):
            raise TypeError(
                f"filter_opt must be bool, but {type(value)} is given"
            )

        self._filter_opt = value
    

    def read_data(self, dispatch_data):

        '''
        read clustering data from dispatch csv files
        
        Aruguments:
            dispatch_data: path of the csv file. 

        Return: 
            numpy array with dispatch data.
        '''

        # One sim year data is one row, read the target rows.
        df_dispatch = pd.read_csv(dispatch_data, nrows = self.years)

        # drop the first column
        df_dispatch_data = df_dispatch.iloc[: , 1:]

        # the first column is the run_index. Put them in an array
        df_index = df_dispatch.iloc[:,0]
        run_index = df_index.to_numpy(dtype = str)

        # In csv files, every run is not in sequence from 0 to 64999. 
        # run indexs are strings of 'run_xxxx.csv', make xxxx into a list of int
        self.index = []
        for run in run_index:
            index_num = re.split('_|\.',run)[1]
            self.index.append(int(index_num))

        # transfer the data to the np.array, dimension of test_years*8736(total hours in one simulation year)
        dispatch_array = df_dispatch_data.to_numpy(dtype = float)

        return dispatch_array


    def _read_input_pmax(self, input_data_path):

        '''
        read the input p_max for each simulation year

        Arguments:
            None

        Return:
            np.ndarray: pmax of each simulation data.
        '''
        # this_file_path = os.getcwd()
        # input_data = os.path.join(this_file_path, '..\\datasets\\prescient_generator_inputs.h5')
        df_input_data = pd.read_hdf(input_data_path)

        # first column is the p_max, from run_0 to run_64799
        df_pmax = df_input_data.iloc[:,1]
        pmax = df_pmax.to_numpy(dtype = float)
        
        return pmax


    def _transform_data(self, dispatch_array, input_data_path):

        '''
        shape the data to the format that tslearn can read.

        Arguments:
            dispatch data in the shape of numpy array. (Can be obtained from self.read_data())

        Return:
            train_data: np.arrya for the tslearn package. Dimension = (self.years*364, 24, 1)
            number of full/zero days: np.array([full_day,zero_day])
        '''
    
        # number of hours in a representative day
        time_len = 24

        # should have 364 day in a year in our simulation
        day_num = int(np.round(len(dispatch_array[0])/time_len))

        # We use the target number of years (self.years) to do the clustering
        dispatch_years = dispatch_array[0:self.years]

        # Need to have the index to do scaling by pmax. 
        dispatch_years_index = self.index[0:self.years]

        pmax = self._read_input_pmax(input_data_path)

        datasets = []

        if self.filter_opt == True:
            full_day = 0
            zero_day = 0
            for year,idx in zip(dispatch_years, dispatch_years_index):
                # scale by the p_max
                pmax_of_year = pmax[idx]
                scaled_year = year/pmax_of_year

                # slice the year data into day data(24 hours a day)
                # filter out full/zero capacity days
                for i in range(day_num):
                    day_data = scaled_year[i*time_len:(i+1)*time_len]
                    # count the day of full/zero capacity factor.
                    if sum(day_data) == 0:
                        zero_day += 1
                    # here should be 24 instead of 1.
                    elif sum(day_data) == 24: 
                        full_day += 1
                    else:
                        # datasets = [day_1, day_2,...,day_xxx], day_xxx is np.array([hour0,hour1,...,hour23])
                        datasets.append(day_data)
            
            # use tslearn package to form the correct data structure.
            train_data = to_time_series_dataset(datasets)

        else:
            for year,idx in zip(dispatch_years, dispatch_years_index):
            # scale by the p_max
                pmax_of_year = pmax[idx]
                scaled_year = year/pmax_of_year

            # slice the year data into day data(24 hours a day)
            
            for i in range(day_num):
                day_data = scaled_year[i*time_len:(i+1)*time_len]
                datasets.append(day_data)
        
            # use tslearn package to form the correct data structure.
            train_data = to_time_series_dataset(datasets)
            full_day = 'filter = False'
            zero_day = 'filter = False'

        return train_data, np.array([full_day,zero_day])


    def cluster_data(self, train_data):

        '''
        cluster the data. Save the model to a json file. 
        
        Arguments:
            train_data: from self.transform_data
            clusters: number of clusters specified
            data_num: index for saving file name.
            save_index: bool, when True, save the cluster center results in json file.
        
        return:
            result path (json) file. 
        '''

        km = TimeSeriesKMeans(n_clusters = self.num_clusters, metric = self.metric, random_state = 0)
        labels = km.fit_predict(train_data)

        return km
