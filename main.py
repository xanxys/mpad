#!/bin/env python
"""
Minimalistic mpad editor.

UI-related handler MUST NOT take more than 100ms.

Always prepare for large data, otherwise make it so obvious that no one will try.
"""
from __future__ import division, print_function
import pygtk
pygtk.require('2.0')
import gtk
import cairo
import sys
import binascii
import math
import msgpack


class Term(object):
    """
    Term GUI element

    compound term have corresponding Segment
    """
    def __init__(self, e):
        self.selected = False
        self.configure(e)

    def set_string(self, s):
        e = type(self.e)(s)
        self.configure(e)

    def configure(self, e):
        self.e = e

        if type(e) is float or type(e) is int or type(e) is bool:
            self.s = str(e)
            self.t = type(e).__name__
        elif type(e) is str:
            summary = e[:30]

            # TODO: do whole checking of possibly long string in background and show it later.
            # in first invocation, only do constant-length search.
            try: 
                self.s = summary.decode('utf-8')
                self.t = 'str'
                if '\x00' in self.s:
                    self.s = binascii.hexlify(summary)
                    self.t = 'binary'
            except UnicodeDecodeError:
                self.s = binascii.hexlify(summary)
                self.t = 'binary'
            
            if len(summary) < len(e):
                self.s += '...[%dB]'%(len(e))
            elif len(summary) == 0:
                self.s += '[0B]'

        elif type(e) is dict:
            self.s = '{%d}'%len(e)
            self.t = 'dict'
        elif type(e) is tuple:
            self.s = '[%d]'%len(e)
            self.t = 'list'
        else:
            self.s = 'error'
            self.t = 'error'
    
    def get_width(self):
        return max(50, 10+6*len(self.s))

    def as_string(self):
        return self.s

    def is_compound(self):
        return type(self.e) is dict or type(self.e) is tuple

    def get_type(self):
        return self.t

class Segment(object):
    def __init__(self, es):
        self.terms = map(Term, es)

        # layout
        self.range = (0, len(self.terms))

    def layout(self, height, hoffset, woffset):
        """
        in range update try to preserve top index

        TODO: remove hoffset from Segment
        """
        term_height = 10
        seg_padding = 5

        # update misc info
        self.top = hoffset
        self.bottom = hoffset+height
        self.height = height
        self.total = len(self.terms)

        # update range
        n_fit = int((height-seg_padding*2)/term_height)
        if len(self.terms) <= n_fit:
            self.range = (0, len(self.terms))
        else: # try to preserve top
            if self.range[0]+n_fit>len(self.terms):
                self.range = (len(self.terms)-n_fit, len(self.terms)) # hit bottom
            else:
                self.range = (self.range[0], self.range[0]+n_fit)

        # update Term. preserve invisible(eg. not in range) Terms as is.
        for (k,term) in enumerate(self.children):
            term.top = hoffset + seg_padding + k*term_height
            term.pos = (woffset, term.top)
            term.left = woffset
            term.bottom = term.top+10
            term.body = term

    def importance(self):
        raw = sum(2 if term.selected else 1 for term in self.terms)
        return math.log(1+raw)

    def on_scroll(self, d):
        """ TODO: smooth scrolling """
        new_range = (self.range[0]+d, self.range[1]+d)

        if 0<=new_range[0] and new_range[1]<=len(self.terms):
            self.range = new_range

    @property
    def children(self):
        return self.terms[self.range[0]:self.range[1]]

class Column(object):
    """ Column consists of Segments or single Term (root) """
    def __init__(self, e):
        pass

    def layout(self, height):
        pass


        
class Base(object):
    def __init__(self, model):
        self.model = model
        self.do_group()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('check-resize', self.on_resize)
        self.window.connect('delete_event', self.on_delete)
        self.window.connect('destroy', gtk.main_quit)
        self.window.connect('key_press_event', self.on_key_press)

        self.darea = gtk.DrawingArea()
        self.darea.set_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.SCROLL_MASK)
        self.darea.connect('expose_event', self.on_expose)
        self.darea.connect('button_press_event', self.on_button_press)
        self.darea.connect('scroll_event', self.on_scroll)
        self.window.add(self.darea)
        self.window.show_all()

        self.config = {
            'font': 'Inconsolata',
            'color_scheme': {
                'int': (0.702,0.806,0.999),
                'float': (0.682,0.506,0.999),
                'str': (0.902,0.859,0.455),
                'binary': (0.902,0.859,0.855),
                'dict': (0.973,0.973,0.949),
                'list': (0.973,0.973,0.949)
            }
        }

    def main(self):
        gtk.main()

    def on_delete(self, w, ev):
        return False

    def on_resize(self, w):
        self.do_layout(*w.get_size())

    def do_group(self):
        levels = {}
        def st(e, lv=0):
            if type(e) is list or type(e) is tuple:
                levels.setdefault(lv,[]).append(Segment(e))
                for x in e:
                    st(x, lv+1)
            elif type(e) is dict:
                es = list(x for pair in e.items() for x in pair)
                levels.setdefault(lv,[]).append(Segment(es))
                for x in es:
                    st(x, lv+1)

        st(self.model)
        self.columns = levels

    def do_layout(self, w, h):
        """ Annotate w/ pos """
        seg_padding = 5

        levels_new = {}
        level_left = 0
        for (i, column) in self.columns.items():
            level_width = max(term.get_width() for seg in column for term in seg.terms)

            segs_new = []
            segs_accum = 0
            sum_importance = sum(seg.importance() for seg in column)
            for (j, seg) in enumerate(column):
                if segs_accum>h:
                    break

                seg_h = max(seg_padding*10, h * seg.importance()/sum_importance)
                seg.layout(seg_h, segs_accum, level_left)

                segs_new.append(seg)
                segs_accum += seg_h

            levels_new[i] = {
                'left': level_left,
                'right': level_left+level_width,
                'segments': segs_new
            }

            level_left += level_width

        self.layout = levels_new

    def on_expose(self, w, ev):
        """
        msgpack view: foreground + background
        background = links, show overall tree structure
        foreground = columns / column = segments / segment = entries + scrollbar

        currently, we're assuming window is wide enough to contain all columns (this is very often true).
        """
        ctx = w.window.cairo_create()
        ctx.set_source_rgb(0.153,0.157,0.133) # 272822
        ctx.paint()

        seg_padding = 5

        # draw links
        for (i, column) in self.layout.items():
            try:
                ls_ix = 0
                for (j, seg) in enumerate(column['segments']):
                    i_link = 0
                    for (k, term) in enumerate(seg.children):
                        if term.is_compound():
                            if i_link%2 == 0:
                                ctx.set_source_rgb(0.2,0.2,0.2)
                            else:
                                ctx.set_source_rgb(0.3,0.3,0.3)

                            # CW
                            ctx.move_to(self.layout[i+1]['left']-30, term.bottom)
                            ctx.line_to(term.left, term.bottom)
                            ctx.line_to(term.left, term.top)
                            ctx.line_to(self.layout[i+1]['left']-30, term.top)
                            ctx.line_to(self.layout[i+1]['left'], self.layout[i+1]['segments'][ls_ix].top+seg_padding/2)
                            ctx.line_to(self.layout[i+1]['left'], self.layout[i+1]['segments'][ls_ix].bottom-seg_padding/2)
                            ctx.fill()
                            ls_ix += 1
                            i_link+=1
            except IndexError:
                import traceback
                traceback.print_exc()

        # draw content
        ctx.select_font_face(self.config['font'], cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

        for column in self.layout.values():
            for seg in column['segments']:
                sb_margin = 2
                sb_width = 6
                # seg_padding does not apply to scroll bar
                # side line shadow
                ctx.set_line_width(6)
                ctx.set_line_cap(cairo.LINE_CAP_BUTT)
                ctx.set_source_rgb(0.1,0.1,0.1)
                ctx.move_to(column['left']+sb_width/2,seg.top+sb_margin)
                ctx.line_to(column['left']+sb_width/2,seg.bottom-sb_margin)
                ctx.stroke()

                # side line
                if seg.total == 0:
                    p0 = 0
                    p1 = 1
                else:
                    p0 = seg.range[0]/(seg.total)
                    p1 = seg.range[1]/(seg.total)
                len_wbar = seg.bottom-seg.top-2*sb_margin

                ctx.set_line_width(2)
                ctx.set_line_cap(cairo.LINE_CAP_BUTT)
                ctx.set_source_rgb(0.8,0.8,0.8)
                ctx.move_to(column['left']+sb_width/2,seg.top+sb_margin+len_wbar*p0)
                ctx.rel_line_to(0, len_wbar*(p1-p0))
                ctx.stroke()

                for (k, term) in enumerate(seg.children):
                    ctx.save()
                    ctx.translate(term.pos[0],term.pos[1])

                    if term.selected:
                        ctx.set_source_rgba(1.00, 1.00, 0.76, 0.3)
                        ctx.rectangle(0,0,50,10)
                        ctx.fill()

                    ctx.translate(5,10)
                    ctx.text_path(term.body.as_string())

                    ctx.set_source_rgb(*self.config['color_scheme'].get(term.body.get_type(), (1,0,0)))
                    ctx.fill()
                    ctx.restore()

    def on_scroll(self, w, ev):
        for column in self.layout.values():
            if not (column['left']<ev.x and ev.x<column['right']):
                continue

            for seg in column['segments']:
                if not (seg.top<ev.y and ev.y<seg.bottom):
                    continue

                # handle scroll
                seg.on_scroll(1 if ev.direction==gtk.gdk.SCROLL_DOWN else -1)
                seg.layout(seg.height, seg.top, column['left'])
                w.queue_draw_area(0,0,*self.window.get_size())
                return

    def on_button_press(self, w, ev):
        def deselect_all():
            for cl in self.layout.values():
                for seg in cl['segments']:
                    for term in seg.children:
                        term.selected = False

        for column in self.layout.values():
            if not (column['left']<ev.x and ev.x<column['right']):
                continue

            for seg in column['segments']:
                if not (seg.top<ev.y and ev.y<seg.bottom):
                    continue

                for term in seg.children:
                    if not (term.pos[1]<ev.y and ev.y<term.pos[1]+10):
                        continue

                    # TODO: multi-select like ST2 in some modifier is present
                    deselect_all()

                    # select this
                    term.selected = True
                    self.edit = term

                    self.do_layout(*self.window.get_size())
                    w.queue_draw_area(0,0,*self.window.get_size())

    def on_key_press(self, w, ev):
        if hasattr(self, 'edit') and self.edit != None:
            print('appended',ev,ev.string)

            if ev.keyval == gtk.gdk.keyval_from_name('BackSpace'):
                self.edit.set_string(self.edit.as_string()[:-1])
            else:
                self.edit.set_string(self.edit.as_string()+ev.string)

            w.queue_draw_area(0,0,*self.window.get_size())

    def resolve_pos(self, pos):
        pass


if __name__ == "__main__":
    try:
        path = sys.argv[1]
        msg = msgpack.unpack(open(path,'rb'))
    except IndexError:
        msg = None

    base = Base((msg,))
    base.main()
