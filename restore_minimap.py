from gi.repository import GObject, Gedit, GtkSource, Gtk, Pango, PeasGtk, Gio
import os

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMAS_PATH = os.path.join(BASE_PATH, 'schemas')

try:
    schema_source = Gio.SettingsSchemaSource.new_from_directory(
        SCHEMAS_PATH,
        Gio.SettingsSchemaSource.get_default(),
        False)
    schema = schema_source.lookup(
        'org.gnome.gedit.plugins.restore_minimap',
        False)
    settings = Gio.Settings.new_full(
        schema,
        None,
        '/org/gnome/gedit/plugins/restore_minimap/')
except:
    settings = None
    print('Init Failed')


class RestoreMinimapPluginPreferences(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):

    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_create_configure_widget(self):
        if not settings:
            return Gtk.Label(label='Error: could not load settings schema')

        check = Gtk.CheckButton.new_with_label(
            'Display minimap on the left side')
        check2 = Gtk.CheckButton.new_with_label('Show separator')
        flag = Gio.SettingsBindFlags.DEFAULT
        settings.bind('display-on-left', check, 'active', flag)
        settings.bind('show-separator', check2, 'active', flag)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, border_width=10)
        box.pack_start(check, False, True, 0)
        box.pack_start(check2, False, True, 0)
        return box


class Bin(Gtk.Bin):
    def __init__(self):
        super().__init__()


class MinimapView(Gtk.Box):
    bin = None
    map = None
    sep = None
    mapview = None

    def __init__(self, view):
        super().__init__(Gtk.Orientation.HORIZONTAL)
        self.bin = Bin()
        self.map = GtkSource.Map()
        self.mapview = Gtk.Box(Gtk.Orientation.HORIZONTAL)

        self.set_font_desc()
        self.map.set_view(view)

        self.sep = Gtk.Separator()

        self.bin.show()
        self.sep.show()
        self.map.show()
        self.mapview.show()

        self.pack_end(self.bin, False, True, 0)
        self.pack_end(self.mapview, False, True, 0)

        self.mapview.pack_end(self.sep, False, True, 0)
        self.mapview.pack_end(self.map, False, True, 0)

        self.on_dir_changed()
        self.on_separator_changed()

    def on_dir_changed(self, *args):
        global settings
        display_on_left = False

        if settings is not None:
            display_on_left = settings.get_boolean('display-on-left')

        if display_on_left:
            self.set_direction(Gtk.TextDirection.LTR)
        else:
            self.set_direction(Gtk.TextDirection.RTL)

        self.hide()
        self.show()

    def on_separator_changed(self, *args):
        global settings
        show_separator = True
        if settings is not None:
            show_separator = settings.get_boolean('show-separator')
        if show_separator:
            self.sep.show()
        else:
            self.sep.hide()

    def set_font_desc(self):
        if not self.map:
            return

        default_font = 'Monospace 1'
        try:
            editor_schema = 'org.gnome.gedit.preferences.editor'
            editor_settings = Gio.Settings.new(editor_schema)
            use_default_font = editor_settings.get_boolean('use-default-font')
            if use_default_font:
                desktop_schema = 'org.gnome.desktop.interface'
                desktop_settings = Gio.Settings.new(desktop_schema)
                default_font = desktop_settings.get_string(
                    'monospace-font-name')
            else:
                default_font = editor_settings.get_string('editor-font')
        except:
            pass

        desc = Pango.FontDescription(default_font)
        desc.set_size(Pango.SCALE * 4)  # set size to 1pt
        desc.set_family(desc.get_family())
        self.map.set_property('font-desc', desc)


class RestoreMinimapPlugin(GObject.Object, Gedit.ViewActivatable):

    view = GObject.property(type=Gedit.View)
    scrolled = None
    frame = None
    minimap = None
    settings_handlers = []

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        if not self.minimap:
            self.minimap = MinimapView(self.view)
        else:
            self.minimap.mapview.show()

        if not self.scrolled:
            self.scrolled = self.view.get_parent()
        if not self.frame:
            self.frame = self.scrolled.get_parent()

        GObject.Object._ref(self.scrolled)

        if self.scrolled.get_parent() == self.frame:
            self.frame.remove(self.scrolled)
            self.minimap.bin.add(self.scrolled)
            self.frame.add(self.minimap)
            GObject.Object._unref(self.scrolled)

        if settings is not None:
            self.settings_handlers = [
                settings.connect('changed::display-on-left',
                                 self.minimap.on_dir_changed),
                settings.connect('changed::show-separator',
                                 self.minimap.on_separator_changed)
            ]

    def do_deactivate(self):
        if self.minimap.bin:
            self.minimap.mapview.hide()

        if settings is not None:
            for handler in self.settings_handlers:
                settings.disconnect(handler)
