from textual.widgets import Button

class HotkeyButton(Button, can_focus=True):
    idx = 0
    
    def __init__(self, hotkey=None, hotkey_description = None, **kwargs):
        if 'label' not in kwargs and hotkey_description != None:
            kwargs['label'] = hotkey_description
        super().__init__(**kwargs)
        
        self.hotkey = hotkey
        self.hotkey_description = hotkey_description
        HotkeyButton.idx += 1
        self.idx = HotkeyButton.idx
        self.app_action = 'press_hotkeybutton_' + str(self.idx)
    
    def update_hotkey(self, hotkey = None, hotkey_description = None, label = None):
        if label == None and hotkey_description != None: self.label = hotkey_description
        self.unbind_hotkey()
        self.hotkey = hotkey
        self.hotkey_description = hotkey_description
        self.bind_hotkey()
    
    def bind_hotkey(self):
        if self.hotkey == None: return
        self.app.bind(self.hotkey, self.app_action, description=self.hotkey_description)
        print("hotkey BOUND for " + str(self.idx))
    
    def unbind_hotkey(self):
        if self.hotkey == None: return
        self.app.unbind(self.hotkey)
        print("hotkey UNBOUND for " + str(self.idx))
    
    def on_mount(self):
        def press_me(): self.press()
        setattr(self.app, 'action_' + self.app_action, press_me)
        self.bind_hotkey()
    
    def on_button_pressed(self):
        print('pressed button ' + str(self.idx))
    
    def watch_disabled(self, disabled_state):
        super().watch_disabled(disabled_state)
        print('disabled', disabled_state)
        if disabled_state: self.unbind_hotkey()
        else: self.bind_hotkey()