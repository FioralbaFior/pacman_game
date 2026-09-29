# Blocking Points and Resolutions

## Assigned package semantics

The assigned generator encodes walls as a 4-bit integer and embeds isolated `42` cells with value 15. Resolution: contain that interpretation in the adapter and expose only game-level traversal methods.

## Middle/corner positions may be unusable

The subject asks for Pac-Man in the middle and ghosts/power pellets in corners, while a generated maze can make an exact requested cell unsuitable. Resolution: choose the nearest walkable cell to each semantic target so the intent remains valid and gameplay never starts inside an obstacle.

## Public platform deployment

A platform upload cannot be completed only by source code because it needs the learner's platform account and final build environment. Resolution: keep a root packaging spec, package command, and in-package instructions so the exact build can be regenerated and then uploaded by the owner.
