"""
Highway Hauler — At initial setup.

Called once when the Evennia database is first created.
Creates the chargen room and all city rooms.
"""


def at_initial_setup():
    from world.build_world import build_world
    build_world()
