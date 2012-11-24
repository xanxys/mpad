#!/bin/env python
"""
/usr/share/applications/xanxys.desktop is needed to launch from gnome menu or nautilus "open with" dialog.

Description of .desktop file: http://developer.gnome.org/integration-guide/stable/desktop-files.html.en

"""
from __future__ import division, print_function
import pygtk
pygtk.require('2.0')
import gtk
import cairo
import sys
import math
import msgpack

class Term(object):
	"""
	Term GUI element
	"""
	def __init__(self, e):
		self.e = e

		if type(e) is float or type(e) is int or type(e) is bool or type(e) is str:
			self.s = str(e)
		elif type(e) is dict:
			self.s = '{%d}'%len(e)
		elif type(e) is tuple:
			self.s = '[%d]'%len(e)
		else:
			self.s = 'error'
	
	def get_width(self):
		return max(50, 10+6*len(self.s))

	def as_string(self):
		return self.s

	def is_compound(self):
		return type(self.e) is dict or type(self.e) is tuple

	def get_type(self):
		return type(self.e).__name__

class Segment(object):
	pass

class Column(object):
	pass

		
class Base:
	def __init__(self, model):
		self.model = model

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("delete_event", self.on_delete)
		self.window.connect('destroy', gtk.main_quit)

		self.darea = gtk.DrawingArea()
		self.darea.set_events(gtk.gdk.SCROLL_MASK)
		self.darea.connect('expose_event', self.on_expose)
		self.darea.connect('scroll_event', self.on_scroll)
		self.window.add(self.darea)
		self.window.show_all()

		self.layout = None

	def main(self):
		gtk.main()

	def on_delete(self, w, ev):
		return False

	def do_layout(self, w, h):
		# format
		levels = {}
		def st(e, lv=0):
			if type(e) is list or type(e) is tuple:
				levels.setdefault(lv,[]).append(map(Term, e))
				for x in e:
					st(x, lv+1)
			elif type(e) is dict:
				es = list(x for pair in e.items() for x in pair)
				levels.setdefault(lv,[]).append(map(Term, es))
				for x in es:
					st(x, lv+1)

		st(self.model)

		# annotate w/ pos
		seg_margin = 5

		levels_new = {}
		level_left = 0
		for (i, segs) in levels.items():
			level_width = max(elem.get_width() for seg in segs for elem in seg)

			seg_top = 0
			segs_new = []
			segs_accum = 0
			sum_log = sum(math.log(1+len(s)) for s in segs)
			for (j, seg) in enumerate(segs):
				if segs_accum>h:
					break

				seg_h = max(seg_margin*2, h * math.log(1+len(seg))/sum_log)
				seg_new = []
				es_accum = 0
				for (k,elem) in enumerate(seg):
					if es_accum>seg_h-seg_margin*2:
						break
					elem_top = seg_top + 10*k
					elem_new = {
						'pos': (level_left, elem_top),
						'left': level_left,
						'top': elem_top,
						'bottom': elem_top+10,
						'body': elem
					}
					seg_new.append(elem_new)
					es_accum += 10

				seg_new = {
					'top': seg_top,
					'bottom': seg_top+seg_h,
					'height': seg_h,
					'children': seg_new,
					'total': len(seg)
				}
				segs_new.append(seg_new)
				seg_top += seg_h
				segs_accum += seg_h

			levels_new[i] = {
				'left': level_left,
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

		self.do_layout(*w.window.get_size())
		ctx.translate(5,0)

		seg_margin = 5

		# draw links
		for (i, level) in self.layout.items():
			try:
				ls_ix = 0
				for (j, seg) in enumerate(level['segments']):
					i_link = 0
					for (k, elem) in enumerate(seg['children']):
						if elem['body'].is_compound():
							if i_link%2 == 0:
								ctx.set_source_rgb(0.2,0.2,0.2)
							else:
								ctx.set_source_rgb(0.3,0.3,0.3)
							# CW
							ctx.move_to(self.layout[i+1]['left']-30, elem['bottom'])
							ctx.line_to(elem['left'], elem['bottom'])
							ctx.line_to(elem['left'], elem['top'])
							ctx.line_to(self.layout[i+1]['left']-30, elem['top'])
							ctx.line_to(self.layout[i+1]['left'], self.layout[i+1]['segments'][ls_ix]['top']+seg_margin/2)
							ctx.line_to(self.layout[i+1]['left'], self.layout[i+1]['segments'][ls_ix]['bottom']-seg_margin/2)
							ctx.fill()
							ls_ix += 1
							i_link+=1
			except IndexError:
				import traceback
				traceback.print_exc()

		# draw content
		color_scheme = {
			'int': (0.702,0.806,0.999),
			'float': (0.682,0.506,0.999),
			'str': (0.902,0.859,0.455),
			'dict': (0.973,0.973,0.949),
			'tuple': (0.973,0.973,0.949)
		}

		for (i, level) in self.layout.items():
			for (j, seg) in enumerate(level['segments']):
				# side line shadow
				ctx.set_line_width(6)
				ctx.set_line_cap(cairo.LINE_CAP_ROUND)
				ctx.set_source_rgb(0.1,0.1,0.1)
				ctx.move_to(level['left'],seg['top']+seg_margin/1.2)
				ctx.line_to(level['left'],seg['bottom']-seg_margin/1.2)
				ctx.stroke()

				# side line (TODO: implement scroll here?)
				if seg['total'] == 0:
					part = 1.0
				else:
					part = max(0.01, len(seg['children']) / seg['total']) # prevent handle getting too small
				ctx.set_line_width(2)
				ctx.set_line_cap(cairo.LINE_CAP_BUTT)
				ctx.set_source_rgb(0.8,0.8,0.8)
				ctx.move_to(level['left'],seg['top']+seg_margin/1.2)
				ctx.line_to(level['left'],min(
					seg['bottom']-seg_margin/1.2,
					seg['top']+seg_margin/1.2 + seg['height']*part))
				ctx.stroke()

				for (k, elem) in enumerate(seg['children']):
					ctx.save()
					ctx.translate(elem['pos'][0]+5,elem['pos'][1]+10)
					ctx.text_path(elem['body'].as_string())

					ctx.set_source_rgb(*color_scheme.get(elem['body'].get_type(), (1,0,0)))
					ctx.fill()
					ctx.restore()

	def on_scroll(self, w, ev):
		print(ev)


if __name__ == "__main__":
	try:
		path = sys.argv[1]
		msg = msgpack.unpack(open(path,'rb'))
	except IndexError:
		msg = [[1,2,3],[4,5,[6,7],8]]

	base = Base(msg)
	base.main()
