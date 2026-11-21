"""Editable NGN-style map layers and display-only town facility controls."""
import copy
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image
from .map_annotations import annotate_portals, annotate_points
from .map_preferences import MapPreferences, DEFAULTS
from .map_text import tr
from .round_slider import RoundSlider

CATEGORIES = ('갑옷', '무기', '방패', '신발', '약국', '여관', '옷', '은행', '잡화', '창고', '길드')


class MapControls:
    def __init__(self, app):
        self.app = app
        self.engine = app.map_engine
        self.preferences = MapPreferences(self.engine)
        self.selected = None
        self.current_map = None
        self.panel = self.dialog = self.guild_menu = None
        self.panel_key = self.panel_layout = self.cache_key = None
        self.cached = None
        self.facility_buttons = {}
        self.guild_close_timer = None
        self.closed = False
        self.engine.map_controls = self
        self.timer = app.root.after(100, self.tick)

    def tr(self, text, code=None):
        return tr(text, code or self.engine.ui_language)

    @property
    def values(self):
        return self.preferences.values

    def sync_map(self, record):
        map_id = (record or {}).get('id')
        if map_id != self.current_map:
            self.current_map = map_id
            self.selected = None
            self.close_guild_menu()
            self.panel_key = self.cache_key = None
        return map_id

    def available(self):
        return [p for p in (self.engine.active_map or {}).get('facilities', [])
                if p.get('category') in CATEGORIES]

    def selected_points(self, record):
        if self.selected is None:
            return []
        kind, value = self.selected
        return [p for p in (record or {}).get('facilities', [])
                if (kind == 'guild' and p['id'] == value and p['category'] == '길드')
                or (kind == 'category' and p['category'] == value and value != '길드')]

    def compose(self, base, record, locale):
        self.sync_map(record)
        key = (id(base), id(record), locale, self.selected)
        if key != self.cache_key:
            image = base.copy() if self.values['terrain'] else Image.new('RGBA', base.size, self.values['background'])
            if record:
                annotate_portals(image, record, locale, self.values['portals'])
                if self.values['navigation']:
                    points = [dict(p, name=self.tr(p['name'])) for p in self.selected_points(record)]
                    annotate_points(image, record, points, self.values['facilities'], locale)
            self.cached, self.cache_key = image, key
        return self.cached.copy()

    def refresh(self):
        self.cache_key = None
        self.update_selection()
        self.engine.render_map()

    def set_pk_enabled(self, enabled):
        values = copy.deepcopy(self.values)
        values['pk'] = bool(enabled)
        self.preferences.save(values)
        if self.dialog is not None and self.dialog.winfo_exists():
            self.pk_variable.set(values['pk'])
        self.refresh()

    def toggle(self):
        values = copy.deepcopy(self.values)
        values['navigation'] = not values['navigation']
        self.preferences.save(values)
        if not values['navigation']:
            self.selected = None
            self.close_guild_menu()
        self.refresh()

    def select(self, kind, value):
        if kind == 'category' and value == '길드':
            return
        target = (kind, value)
        self.selected = None if self.selected == target else target
        self.close_guild_menu()
        self.refresh()
        hwnd = getattr(self.app, 'target_hwnd', None)
        if hwnd:
            from .window_attachment import focus_native_window
            self.app.root.after_idle(lambda: focus_native_window(hwnd))

    def update_selection(self):
        for category, button in self.facility_buttons.items():
            chosen = self.selected == ('category', category) or (
                category == '길드' and self.selected is not None and self.selected[0] == 'guild')
            button.configure(bg='#80633b' if chosen else '#241d15',
                             fg='#ffe09a' if chosen else '#d7c5a3',
                             relief='sunken' if chosen else 'flat')

    def build_panel(self):
        from .window_attachment import make_noactivate_toolwindow
        from modal_window import modal_font_family
        if self.panel is None:
            self.panel = tk.Toplevel(self.engine.map_window)
            self.panel.withdraw()
            self.panel.overrideredirect(True)
            self.panel.configure(bg='#d8b15a')
            make_noactivate_toolwindow(self.panel)
        family = modal_font_family(self.panel, self.engine.ui_language)
        available = {p['category'] for p in self.available()}
        for i, category in enumerate(CATEGORIES):
            if category not in self.facility_buttons:
                frame = tk.Frame(self.panel, bg='#241d15')
                frame.grid(row=0, column=i, padx=(1, 0), pady=1)
                frame.grid_propagate(False)
                button = tk.Button(frame, takefocus=False, bd=0, highlightthickness=0, padx=0, pady=0,
                                   activebackground='#80633b', activeforeground='#ffe09a', disabledforeground='#706453')
                button.place(x=0, y=0, relwidth=1, relheight=1)
                if category == '길드':
                    button.bind('<Enter>', self.open_guild_menu)
                    button.bind('<Leave>', self.schedule_guild_close)
                else:
                    button.configure(command=lambda c=category: self.select('category', c))
                self.facility_buttons[category] = button
            button = self.facility_buttons[category]
            caption = self.tr(category)
            if self.engine.ui_language == 'EN':
                caption = dict(zip(CATEGORIES, ('Arm', 'Wpn', 'Shld', 'Shoe', 'Pot', 'Inn', 'Clth', 'Bank', 'Item', 'Stor', 'Guild')))[category]
            button.configure(text=caption, font=(family, 8), state='normal' if category in available else 'disabled')
        self.update_selection()
        self.panel_layout = None

    def cancel_guild_close(self, event=None):
        if self.guild_close_timer is not None:
            self.app.root.after_cancel(self.guild_close_timer)
            self.guild_close_timer = None

    def schedule_guild_close(self, event=None):
        self.cancel_guild_close()
        self.guild_close_timer = self.app.root.after(220, self.close_guild_if_outside)

    def close_guild_if_outside(self):
        self.guild_close_timer = None
        x, y = self.app.root.winfo_pointerxy()
        for widget in (self.guild_menu, self.facility_buttons.get('길드')):
            if widget is not None and widget.winfo_exists() and widget.winfo_viewable():
                if widget.winfo_rootx() <= x < widget.winfo_rootx() + widget.winfo_width() and widget.winfo_rooty() <= y < widget.winfo_rooty() + widget.winfo_height():
                    return
        self.close_guild_menu()

    def close_guild_menu(self):
        self.cancel_guild_close()
        if self.guild_menu is not None:
            self.guild_menu.destroy()
            self.guild_menu = None

    def open_guild_menu(self, event=None):
        self.cancel_guild_close()
        if self.guild_menu is not None:
            return
        guilds = [p for p in self.available() if p['category'] == '길드']
        if not guilds or self.panel is None or not self.panel.winfo_viewable():
            return
        from .window_attachment import attach_above, native_window_handle, make_noactivate_toolwindow
        from modal_window import modal_font_family
        menu = self.guild_menu = tk.Toplevel(self.panel)
        menu.withdraw()
        menu.overrideredirect(True)
        menu.configure(bg='#d8b15a')
        make_noactivate_toolwindow(menu)
        menu.bind('<Enter>', self.cancel_guild_close)
        menu.bind('<Leave>', self.schedule_guild_close)
        family = modal_font_family(menu, self.engine.ui_language)
        side = self.panel_layout[2] if self.panel_layout else self.values['facilities']['button_size']
        font = (family, -max(8, round(11 * side / 36)))
        padding = max(6, round(side / 3))
        metrics = tkfont.Font(font=font)
        width = max(side * 3, max(metrics.measure(self.tr(p['name'])) for p in guilds) + padding * 2)
        for p in guilds:
            chosen = self.selected == ('guild', p['id'])
            normal_bg = '#80633b' if chosen else '#241d15'
            normal_fg = '#ffe09a' if chosen else '#d7c5a3'
            row = tk.Frame(menu, width=width, height=side, bg=normal_bg)
            row.pack(fill='x', padx=1, pady=1)
            row.pack_propagate(False)
            button = tk.Button(row, text=self.tr(p['name']), anchor='w', takefocus=False,
                               bg=normal_bg, fg=normal_fg,
                               activebackground='#a17b43', activeforeground='#fff1c9',
                               relief='flat', highlightthickness=0,
                               bd=0, padx=padding, pady=0, font=font,
                               command=lambda value=p['id']: self.select('guild', value))
            button.pack(fill='both', expand=True)
            def enter(event, widget=button):
                self.cancel_guild_close()
                widget.configure(bg='#a17b43', fg='#fff1c9')
            def leave(event, widget=button, bg=normal_bg, fg=normal_fg):
                widget.configure(bg=bg, fg=fg)
                self.schedule_guild_close()
            button.bind('<Enter>', enter)
            button.bind('<Leave>', leave)
        menu.update_idletasks()
        button = self.facility_buttons['길드']
        x, y = button.winfo_rootx(), self.panel.winfo_y() + self.panel.winfo_height()
        bounds = getattr(self.app, 'client_rect', None)
        if bounds:
            left, top, right, bottom = bounds
            x = max(left, min(x, right - menu.winfo_reqwidth()))
            if y + menu.winfo_reqheight() > bottom:
                y = self.panel.winfo_y() - menu.winfo_reqheight()
            y = max(top, y)
        menu.geometry(f'+{x}+{y}')
        attach_above(menu, native_window_handle(self.panel), x=x, y=y)
        menu.deiconify()
        make_noactivate_toolwindow(menu)

    def language_changed(self):
        self.close_guild_menu()
        opened = self.dialog is not None and self.dialog.winfo_exists()
        if opened:
            self.dialog.destroy()
            self.dialog = None
        self.panel_key = None
        self.refresh()
        if opened:
            self.open_settings()

    def tick(self):
        if self.closed:
            return
        try:
            from .window_attachment import attach_above, is_minimized, native_window_handle, owner_group_is_foreground, make_noactivate_toolwindow
            engine = self.engine
            map_id = self.sync_map(engine.active_map)
            hwnd = getattr(self.app, 'target_hwnd', None)
            visible = (self.values['navigation'] and bool(self.available()) and hwnd
                       and engine.minimap_enabled and not engine.world_map_mode and not engine.no_map_data_visible
                       and not getattr(self.app, 'overlays_temporarily_hidden', False)
                       and not getattr(self.app, 'client_overlays_unavailable', False)
                       and engine.map_window.winfo_viewable() and not is_minimized(hwnd))
            if visible:
                key = (map_id, engine.ui_language, id(engine.active_map))
                if key != self.panel_key:
                    self.close_guild_menu()
                    self.build_panel()
                    self.panel_key = key
                bounds = getattr(self.app, 'client_rect', None)
                requested_side = self.values['facilities']['button_size']
                side = max(12, min(requested_side, (bounds[2] - bounds[0] - 4) // len(CATEGORIES) - 1)) if bounds else requested_side
                width, height = len(CATEGORIES) * (side + 1) + 1, side + 2
                x, y = engine.map_window.winfo_x(), engine.map_window.winfo_y() - height - 3
                if bounds:
                    left, top, right, bottom = bounds
                    x = max(left, min(x, right - width))
                    if y < top:
                        y = engine.map_window.winfo_y() + engine.map_window.winfo_height() + 3
                    y = max(top, min(y, bottom - height))
                layout = (x, y, side)
                if layout != self.panel_layout:
                    self.close_guild_menu()
                    for button in self.facility_buttons.values():
                        button.master.configure(width=side, height=side)
                        font = tkfont.Font(font=button.cget('font'))
                        size = max(8, round(11 * side / 36))
                        font.configure(size=-size)
                        while size > 6 and font.measure(button.cget('text')) > side - 4:
                            size -= 1
                            font.configure(size=-size)
                        button.configure(font=(font.actual('family'), -size))
                    self.panel.geometry(f'{width}x{height}+{x}+{y}')
                    self.panel_layout = layout
                if not self.panel.winfo_viewable() or layout != getattr(self, 'attached_layout', None):
                    attach_above(self.panel, native_window_handle(engine.map_window), x=x, y=y)
                    self.panel.deiconify()
                    make_noactivate_toolwindow(self.panel)
                    self.attached_layout = layout
                if self.guild_menu is not None and not owner_group_is_foreground(hwnd, native_window_handle(self.panel)):
                    self.close_guild_menu()
            else:
                self.close_guild_menu()
                if self.panel is not None:
                    self.panel.withdraw()
        finally:
            if not self.closed:
                self.timer = self.app.root.after(100, self.tick)

    def close(self):
        self.closed = True
        self.app.root.after_cancel(self.timer)
        self.close_guild_menu()
        for window in (self.panel, self.dialog):
            if window is not None and window.winfo_exists():
                window.destroy()

    def open_settings(self):
        self.close_guild_menu()
        from modal_window import place_modal, bind_modal_escape, bind_modal_drag, activate_modal, modal_font_family
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.deiconify(); self.dialog.lift(); activate_modal(self.dialog); return
        win = self.dialog = tk.Toplevel(self.app.root)
        win.title(self.tr('지도 설정'))
        win.overrideredirect(True)
        win.transient(self.app.root)
        win.configure(bg='#d8b15a')
        family = modal_font_family(win, getattr(self.engine, 'ui_language', 'KR'))
        bg, fg = '#17130f', '#fff1c9'
        panel = tk.Frame(win, bg=bg, padx=16, pady=12)
        panel.pack(fill='both', expand=True, padx=1, pady=1)
        title = tk.Label(panel, text=self.tr('지도 설정'), bg='#5a4932', fg='#ffe09a',
                         font=(family,11,'bold'), anchor='w', padx=12, pady=10)
        title.pack(fill='x', pady=(0,12))
        tabs = tk.Frame(panel, bg=bg); tabs.pack(fill='x', pady=(0,12))
        body = tk.Frame(panel, bg=bg); body.pack(fill='both', expand=True)
        variables, pages, buttons = {}, {}, {}
        def button(parent, text, command):
            return tk.Button(parent, text=self.tr(text), command=command, bg='#6b5537', fg=fg,
                             activebackground='#806846', activeforeground='white',
                             relief='flat', bd=0, padx=12, pady=7, font=(family,9))
        def show(section):
            palette.place_forget()
            for key, page in pages.items():
                page.grid_remove()
                buttons[key].configure(bg='#6b5537' if key==section else '#2a2118')
            pages[section].grid(row=0,column=0,sticky='nsew')
        labels = {'terrain':'지형 이미지', 'pk':'PK 표시', 'reaper_timer':'사신의 칼날 시간 표시',
                  'visible':'표시', 'labels':'이름 표시', 'color':'점 색상', 'outline':'점 테두리',
                  'radius':'점 크기', 'font_size':'글자 크기', 'font_weight':'글자 굵기', 'text_color':'글자 색상',
                  'label_background':'라벨 배경 표시', 'background':'배경 색상', 'border':'라벨 테두리',
                  'leaders':'연결선 표시', 'leader_color':'연결선 색상', 'button_size':'시설버튼 크기'}
        # A child frame stays in the settings window's native z-order.
        palette=tk.Frame(body,bg='#2a2118',highlightbackground='#d8b15a',highlightthickness=1,padx=12,pady=10)
        palette_title=tk.Label(palette,bg='#2a2118',fg=fg,font=(family,10,'bold'))
        palette_title.grid(row=0,column=0,columnspan=5,sticky='w',pady=(0,8))
        button(palette,'닫기',palette.place_forget).grid(row=0,column=5,pady=(0,8))
        palette_target=[None]
        def pick(color):
            if palette_target[0] is not None:palette_target[0].set(color)
            palette.place_forget()
        presets=('#ffffff','#b8b8b8','#000000','#ff3030','#ff8c32','#ffe500',
                 '#7cdd63','#44ddeb','#4488ff','#bd83ff','#ff80b5','#d8b15a',
                 '#101820','#182733','#637586','#17130f','#5a4932','#6b5537')
        for i,color in enumerate(presets):
            cell=tk.Frame(palette,width=38,height=32,bg='#2a2118')
            cell.grid(row=1+i//6,column=i%6,padx=3,pady=3);cell.grid_propagate(False)
            tk.Button(cell,bg=color,activebackground=color,relief='flat',bd=0,
                      command=lambda c=color:pick(c)).place(x=0,y=0,relwidth=1,relheight=1)
        def field_label(section, key):
            return self.tr('지형 숨김 시 배경색' if section is None and key == 'background' else labels[key])

        def choose_palette(var,key,section):
            palette_target[0]=var
            palette_title.configure(text=field_label(section,key))
            palette.place(relx=.5,rely=.5,anchor='center');palette.lift()
        for section, name in [(None,'기본'),('portals','이동 지점'),('player','내 위치'),('facilities','마을 시설')]:
            frame = pages[section] = tk.Frame(body, bg=bg)
            tab = buttons[section] = button(tabs,name,lambda key=section:show(key))
            tab.pack(side='left',expand=True,fill='x',padx=2)
            data = self.values if section is None else self.values[section]
            keys = ['terrain','pk','reaper_timer','background'] if section is None else list(data)
            for index,key in enumerate(keys):
                value=data[key]
                var=tk.BooleanVar(win,value=value) if isinstance(value,bool) else tk.StringVar(win,value=str(value))
                variables[(section,key)]=var
                row=tk.Frame(frame,bg=bg,width=502 if section is None else 244,height=36)
                row.grid(row=index%7,column=index//7,sticky='ew',padx=(0,14),pady=3)
                row.grid_propagate(False)
                row.columnconfigure(0,weight=1)
                if key == 'button_size':
                    tk.Label(row,text=field_label(section,key),bg=bg,fg=fg,font=(family,9)).grid(row=0,column=0,sticky='w')
                    slider=RoundSlider(row,value=value,length=90,minimum=24,maximum=72,
                                       background=bg,trough='#2a2118',fill='#d8b15a')
                    slider.grid(row=0,column=1,padx=(4,2),pady=8)
                    number=tk.Label(row,text=f'{value}',width=3,bg=bg,fg='#bda982',font=(family,9))
                    number.grid(row=0,column=2)
                    def sync_slider(*args,v=var,w=slider,label=number):
                        w.set(v.get())
                        label.configure(text=str(w.get()))
                    var.trace_add('write',sync_slider)
                    for event in ('<Button-1>','<B1-Motion>','<ButtonRelease-1>','<Left>','<Right>'):
                        slider.bind(event,lambda event,v=var,w=slider:v.set(str(w.get())),add='+')
                elif isinstance(value,bool):
                    tk.Checkbutton(row,text=field_label(section,key),variable=var,bg=bg,fg=fg,selectcolor='#2a2118',
                                   activebackground=bg,activeforeground=fg,font=(family,10)).grid(row=0,column=0,columnspan=2,sticky='w')
                else:
                    tk.Label(row,text=field_label(section,key),bg=bg,fg=fg,font=(family,10)).grid(row=0,column=0,sticky='w')
                    if isinstance(value,int):
                        lo,hi={'radius':(2,14),'font_size':(9,28),'font_weight':(100,900),'button_size':(24,72)}[key]
                        tk.Spinbox(row,from_=lo,to=hi,increment=100 if key=='font_weight' else 1,textvariable=var,width=5,bg='#2a2118',fg=fg,
                                   buttonbackground='#6b5537',insertbackground=fg,relief='flat',font=(family,10)).grid(row=0,column=1,pady=4)
                    else:
                        swatch=tk.Button(row,width=6,bg=value,activebackground=value,relief='flat',bd=0)
                        swatch.configure(command=lambda v=var,k=key,s=section:choose_palette(v,k,s))
                        swatch.grid(row=0,column=1,pady=4)
                        var.trace_add('write',lambda *args,v=var,w=swatch:w.configure(bg=v.get(),activebackground=v.get()))
            # Keep every tab at the same size, including the compact general tab.
            frame.configure(width=516,height=294)
            frame.grid_propagate(False)
        self.pk_variable = variables[(None, 'pk')]
        show(None)
        footer=tk.Frame(panel,bg=bg);footer.pack(fill='x',pady=(12,0))
        status=tk.StringVar(win,value=self.tr('변경 즉시 저장'))
        resetting=False
        def save(values):
            try:
                self.preferences.save(values)
            except OSError:
                status.set(self.tr('저장 실패 · 다시 변경해 주세요'))
                return
            status.set(self.tr('변경 즉시 저장'))
            self.refresh()
        def changed(section,key,var):
            if resetting:return
            value=var.get()
            if section and key in ('radius','font_size','font_weight','button_size'):
                # Empty/partial text while typing must not overwrite the last valid value.
                try:value=int(value)
                except ValueError:return
                lo,hi={'radius':(2,14),'font_size':(9,28),'font_weight':(100,900),'button_size':(24,72)}[key]
                if not lo <= value <= hi:return
            values=copy.deepcopy(self.values)
            target=values if section is None else values[section]
            if target[key]==value:return
            target[key]=value
            save(values)
        for (section,key),var in variables.items():
            var.trace_add('write',lambda *args,s=section,k=key,v=var:changed(s,k,v))
        def close():
            win.destroy();self.dialog=None
        def reset():
            nonlocal resetting
            resetting=True
            values=copy.deepcopy(self.values)
            for (section,key),var in variables.items():
                value=(DEFAULTS if section is None else DEFAULTS[section])[key]
                var.set(value)
                (values if section is None else values[section])[key]=value
            resetting=False
            save(values)
        button(footer,'기본값',reset).pack(side='left')
        tk.Label(footer,textvariable=status,bg=bg,fg='#b9aa91',font=(family,9)).pack(side='left',padx=12)
        button(footer,'닫기',close).pack(side='right')
        _,bounds=place_modal(win,minimum_width=550,minimum_height=440,position_key='map_display_settings')
        # Owned chain: settings -> toolbar -> minimap -> game. Never global topmost.
        from godinavi.window_attachment import attach_above, native_window_handle
        attach_above(win, native_window_handle(self.app.root))
        bind_modal_drag(win,(title,),lambda:bounds,'map_display_settings')
        bind_modal_escape(win,close)

