mpad
=============

Minimalistic MessagePack data viewer written with pygtk.

![screenshot](https://raw.github.com/xanxys/mpad/master/screenshot.png)

TODO
-----
* ensure all portion of any data is visible and editable in reasonable time
* saving/opening (or autosaving and undo/redo)
* add menu
* add Input Method support
* add copy/pasting
* adding/deleting values
* multi-selection like ST2

NOT TODO
-----
* implement schema
* corrupt file handling
* stream handling
* Turing-complete plugins


Installation
-----
- put main.py somewhere convenient
- rewrite Exec section of mpad.desktop to point to the main.py
- put mpad.desktop under /usr/share/applications
- you can now use nautilus "open with..." to associate mpad
