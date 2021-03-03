##############################################################################
# Institute for the Design of Advanced Energy Systems Process Systems
# Engineering Framework (IDAES PSE Framework) Copyright (c) 2018-2020, by the
# software owners: The Regents of the University of California, through
# Lawrence Berkeley National Laboratory,  National Technology & Engineering
# Solutions of Sandia, LLC, Carnegie Mellon University, West Virginia
# University Research Corporation, et al. All rights reserved.
#
# Please see the files COPYRIGHT.txt and LICENSE.txt for full copyright and
# license information, respectively. Both files are also available online
# at the URL "https://github.com/IDAES/idaes-pse".
##############################################################################
"""
Basic tests for H2 property package
"""
import pytest

from pyomo.environ import ConcreteModel, value, SolverFactory

from h2_ideal_vap import configuration

from idaes.core import FlowsheetBlock
from idaes.generic_models.properties.core.generic.generic_property \
    import GenericParameterBlock

m = ConcreteModel()

m.fs = FlowsheetBlock(default={"dynamic": False})

m.fs.props = GenericParameterBlock(default=configuration)

m.fs.state = m.fs.props.build_state_block(
    m.fs.config.time, default={"defined_state": True})

# Fix state
m.fs.state[0].flow_mol.fix(1)
m.fs.state[0].mole_frac_comp.fix(1)
m.fs.state[0].temperature.fix(300)
m.fs.state[0].pressure.fix(101325)

# Initialize state
m.fs.state.initialize()

# Verify against NIST tables
assert value(m.fs.state[0].cp_mol) == pytest.approx(28.85, rel=1e-2)
assert value(m.fs.state[0].enth_mol) == pytest.approx(43.4, rel=1e-2)
assert value(m.fs.state[0].entr_mol) == pytest.approx(130.9, rel=1e-2)
assert (value(m.fs.state[0].gibbs_mol/m.fs.state[0].temperature) ==
        pytest.approx(-130.7, rel=1e-2))

# Try another temeprature
m.fs.state[0].temperature.fix(500)

solver = SolverFactory('ipopt')
solver.solve(m.fs)

assert value(m.fs.state[0].cp_mol) == pytest.approx(29.26, rel=1e-2)
assert value(m.fs.state[0].enth_mol) == pytest.approx(5880, rel=1e-2)
assert value(m.fs.state[0].entr_mol) == pytest.approx(145.7, rel=1e-2)
assert (value(m.fs.state[0].gibbs_mol/m.fs.state[0].temperature) ==
        pytest.approx(-134.0, rel=1e-2))

# Try another temeprature
m.fs.state[0].temperature.fix(900)

solver = SolverFactory('ipopt')
solver.solve(m.fs)

assert value(m.fs.state[0].cp_mol) == pytest.approx(29.88, rel=1e-2)
assert value(m.fs.state[0].enth_mol) == pytest.approx(17680, rel=1e-2)
assert value(m.fs.state[0].entr_mol) == pytest.approx(163.1, rel=1e-2)
assert (value(m.fs.state[0].gibbs_mol/m.fs.state[0].temperature) ==
        pytest.approx(-143.4, rel=1e-2))