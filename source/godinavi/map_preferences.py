"""Validated persistent display preferences for map layers."""
import copy
import re

LAYER_DEFAULT = dict(visible=True, labels=True, color='#ff3030', outline='#000000',
                     radius=5, font_size=14, font_weight=600, text_color='#ffffff', label_background=True,
                     background='#182733', border='#637586', leaders=True, leader_color='#aeb8c2')
DEFAULTS = {'terrain':True,'background':'#101820','pk':True,'navigation':True,
            'portals':dict(LAYER_DEFAULT),
            'facilities':dict(LAYER_DEFAULT,color='#44ddeb',radius=7,button_size=36),
            'player':dict(LAYER_DEFAULT,color='#ffe500',radius=7,labels=False,leaders=False)}


def normalize(values):
    result=copy.deepcopy(DEFAULTS)
    if not isinstance(values,dict):return result
    for key,default in DEFAULTS.items():
        if isinstance(default,bool):
            if type(values.get(key)) is bool:result[key]=values[key]
        elif isinstance(default,str):
            if re.fullmatch(r'#[0-9a-fA-F]{6}',str(values.get(key,''))):result[key]=values[key]
        elif isinstance(values.get(key),dict):
            for name,d in default.items():
                v=values[key].get(name)
                if isinstance(d,bool) and type(v) is bool:result[key][name]=v
                elif isinstance(d,int) and type(v) is int:
                    lo,hi={'radius':(2,14),'font_size':(9,28),'font_weight':(100,900),'button_size':(24,72)}[name]
                    result[key][name]=min(hi,max(lo,v))
                elif isinstance(d,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',str(v)):
                    result[key][name]=v
    return result


class MapPreferences:
    def __init__(self, engine):
        self.engine = engine
        self.values = normalize(engine.config.get('map_display', {}))
        # Preserve the previous effective visibility when merging the two switches.
        self.values['pk'] = self.values['pk'] and bool(engine.config.get('pk_zone_alert_enabled', True))
        engine.config['pk_zone_alert_enabled'] = self.values['pk']

    def save(self, values):
        from map_engine import save_config
        normalized = normalize(values)
        previous = self.engine.config.get('map_display')
        previous_pk = self.engine.config.get('pk_zone_alert_enabled', True)
        self.engine.config['map_display'] = normalized
        self.engine.config['pk_zone_alert_enabled'] = normalized['pk']
        try:
            save_config(self.engine.config)
        except OSError:
            self.engine.config['pk_zone_alert_enabled'] = previous_pk
            if previous is None:
                self.engine.config.pop('map_display', None)
            else:
                self.engine.config['map_display'] = previous
            raise
        self.values = normalized
