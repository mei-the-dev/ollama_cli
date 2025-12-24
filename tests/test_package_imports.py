def test_package_imports():
    import importlib
    pkg = importlib.import_module('singularity')
    # ensure expected modules are importable
    assert hasattr(pkg, '__version__')
    mod = importlib.import_module('singularity.cli')
    assert hasattr(mod, 'get_cli')
    # agent shim
    agent_mod = importlib.import_module('singularity.agent')
    assert hasattr(agent_mod, 'SingularityAgent')
