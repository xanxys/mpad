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

class Base:
	def __init__(self, model):
		self.model = model

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("delete_event", self.on_delete)
		self.window.connect('destroy', gtk.main_quit)

		self.darea = gtk.DrawingArea()
		self.darea.connect('expose_event', self.on_expose)
		self.window.add(self.darea)
		self.window.show_all()

	def main(self):
		gtk.main()

	def on_delete(self, w, ev):
		return False

	def on_expose(self, w, ev):
		ctx = w.window.cairo_create()
		ctx.set_source_rgb(0.153,0.157,0.133) # 272822
		ctx.paint()

		# format
		levels = {}
		def to_flat(e):
			if type(e) is list or type(e) is tuple:
				return '[%d]'%len(e)
			elif type(e) is dict:
				return '{%d}'%len(e)
			else:
				return e

		def st(e, lv=0):
			if type(e) is list or type(e) is tuple:
				levels.setdefault(lv,[]).append(map(to_flat, e))
				for x in e:
					st(x, lv+1)
			elif type(e) is dict:
				es = list(x for pair in e.items() for x in pair)
				levels.setdefault(lv,[]).append(map(to_flat, es))
				for x in es:
					st(x, lv+1)

		st(self.model)

		# annotate w/ pos
		_, h = w.window.get_size()
		levels_new = {}
		for (i, segs) in levels.items():
			level_left = i*100

			seg_top = 0
			segs_new = []
			for (j, seg) in enumerate(segs):
				seg_h = h * math.log(len(seg))/sum(math.log(len(s)) for s in segs)
				seg_new = []
				for (k,elem) in enumerate(seg):
					elem_top = seg_top + 10*k
					elem_new = {
						'pos': (level_left, elem_top),
						'body': elem
					}
					seg_new.append(elem_new)
				seg_new = {
					'top': seg_top,
					'bottom': seg_top+seg_h,
					'children': seg_new
				}
				segs_new.append(seg_new)
				seg_top += seg_h

			levels_new[i] = {
				'left': level_left,
				'segments': segs_new
			}

		#print(levels_new)
		# 
		ctx.translate(5,0)


		# draw links
		for (i, level) in levels_new.items():

			ls_ix = 0
			for (j, seg) in enumerate(level['segments']):
				seg_h = h * math.log(len(seg))/sum(math.log(len(s)) for s in segs)
				for (k, elem) in enumerate(seg['children']):
					dont_draw = k*10+10>seg_h

					if type(elem['body']) is str and (elem['body'][0] == '[' or elem['body'][0] == '{'):
						if not dont_draw:
							ctx.set_source_rgb(0.3,0.3,0.3)
							ctx.move_to(elem['pos'][0]+10, elem['pos'][1]+10)
							ctx.line_to(levels_new[i+1]['left'], levels_new[i+1]['segments'][ls_ix]['top']+5)
							ctx.line_to(levels_new[i+1]['left'], levels_new[i+1]['segments'][ls_ix]['bottom']-5)
							ctx.fill()
						ls_ix += 1

		# draw cont
		_, h = w.window.get_size()
		for (i, segs) in levels.items():
			ctx.save()
			ctx.translate(i*100,0)

			for (j, seg) in enumerate(segs):
				seg_h = h * math.log(len(seg))/sum(math.log(len(s)) for s in segs)
				ctx.set_source_rgb(0.8,0.9,0.8)
				ctx.move_to(0,5)
				ctx.line_to(0,seg_h-5)
				ctx.stroke()

				ctx.save()
				ctx.translate(5,15)
				for (k, elem) in enumerate(seg):
					if k*10+10>seg_h:
						break

					if type(elem) is int:
						ctx.set_source_rgb(0.682,0.506,0.999) # #AE81FF
					else:
						ctx.set_source_rgb(0.973,0.973,0.949) # #F8F8F2
					ctx.text_path(str(elem))
					ctx.fill()
					ctx.translate(0, 10)
				ctx.restore()

				ctx.translate(0,seg_h)

			ctx.restore()


if __name__ == "__main__":
	try:
		path = sys.argv[1]
		msg = msgpack.unpack(open(path,'rb'))
	except IndexError:
		msg = [[1,2,3],[4,5,[6,7],8]]

	base = Base(msg)
	base.main()
