"""Handle image reading, writing and plotting plugins.

"""

__all__ = ['use', 'load', 'available', 'call']

import warnings
from ConfigParser import ConfigParser
import os.path
from glob import glob

plugin_store = {'imread': [],
                'imsave': [],
                'imshow': [],
                '_app_show': []}

plugin_provides = {}
plugin_module_name = {}

def _scan_plugins():
    """Scan the plugins directory for .ini files and parse them
    to gather plugin meta-data.

    """
    pd = os.path.dirname(__file__)
    ini = glob(os.path.join(pd, '*.ini'))

    for f in ini:
        cp = ConfigParser()
        cp.read(f)
        name = cp.sections()[0]
        provides = [s.strip() for s in cp.get(name, 'provides').split(',')]
        valid_provides = [p for p in provides if p in plugin_store]

        for p in provides:
            if not p in plugin_store:
                print "Plugin `%s` wants to provide non-existent `%s`." \
                      " Ignoring." % (name, p)

        plugin_provides[name] = valid_provides
        plugin_module_name[name] = os.path.basename(f)[:-4]

_scan_plugins()

def call(kind, *args, **kwargs):
    """Find the appropriate plugin of 'kind' and execute it.

    Parameters
    ----------
    kind : {'show', 'save', 'read'}
        Function to look up.
    plugin : str, optional
        Plugin to load.  Defaults to None, in which case the first
        matching plugin is used.
    *args, **kwargs : arguments and keyword arguments
        Passed to the plugin function.

    """
    if not kind in plugin_store:
        raise ValueError('Invalid function (%s) requested.' % kind)

    plugin_funcs = plugin_store[kind]
    if len(plugin_funcs) == 0:
        raise RuntimeError('''No suitable plugin registered for %s.

You may load I/O plugins with the `scikits.image.io.load_plugin`
command.  A list of all available plugins can be found using
`scikits.image.io.plugins()`.''' % kind)

    plugin = kwargs.pop('plugin', None)
    if plugin is None:
        _, func = plugin_funcs[0]
    else:
        try:
            func = [f for (p,f) in plugin_funcs if p == plugin][0]
        except IndexError:
            raise RuntimeError('Could not find the plugin "%s" for %s.' % \
                               (plugin, kind))

    return func(*args, **kwargs)

def use(name, kind=None):
    """Set the default plugin for a specified operation.

    Parameters
    ----------
    name : str
        Name of plugin.
    kind : {'save', 'read', 'show'}, optional
        Set the plugin for this function.  By default,
        the plugin is set for all functions.

    Examples
    --------

    Use Python Imaging Library to read images:

    >>> from scikits.image.io import plugin
    >>> plugin.use('PIL', 'read')

    """
    if kind is None:
        kind = plugin_store.keys()
    else:
        kind = [kind]
        if not kind in plugin_provides[name]:
            raise RuntimeError("Plugin %s does not support `%s`." % \
                               (name, kind))

    if not name in available(loaded=True):
        raise RuntimeError("No plugin '%s' has been loaded." % name)

    for k in kind:
        if not k in plugin_store:
            raise RuntimeError("'%s' is not a known plugin function." % k)

        funcs = plugin_store[k]

        # Shuffle the plugins so that the requested plugin stands first
        # in line
        funcs = [(n, f) for (n, f) in funcs if n == name] + \
                [(n, f) for (n, f) in funcs if n != name]

        plugin_store[k] = funcs

def available(loaded=False):
    """List available plugins.

    Parameters
    ----------
    loaded : bool
        If True, show only those plugins currently loaded.  By default,
        all plugins are shown.

    """
    from copy import deepcopy
    active_plugins = set()
    for k in plugin_store:
        for plugin, fname in plugin_store[k]:
            active_plugins.add(plugin)

    d = {}
    for plugin in plugin_provides:
        if not loaded or plugin in active_plugins:
            d[plugin] = [f for f in plugin_provides[plugin] \
                         if not f.startswith('_')]

    return d

def load(plugin):
    """Load the given plugin.

    Parameters
    ----------
    plugin : str
        Name of plugin to load.

    See Also
    --------
    plugins : List of available plugins

    """
    if not plugin in plugin_module_name:
        raise ValueError("Plugin %s not found." % plugin)
    else:
        modname = plugin + "_plugin"
        plugin_module = __import__('scikits.image.io._plugins.' + modname,
                                   fromlist=[modname])

    provides = plugin_provides[plugin]
    for p in provides:
        if not hasattr(plugin_module, p):
            print "Plugin %s does not provide %s as advertised.  Ignoring." % \
                  (plugin, p)
        else:
            store = plugin_store[p]
            func = getattr(plugin_module, p)
            if not func in store:
                store.insert(0, (plugin, func))

