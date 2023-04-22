import logging
import pymel.core as pm

from rigbaukasten.utils import errorutl, attrutl, pymelutl

RIG_SET_SUFFIX = 'RIGSET'


def force_rigset_suffix(name):
    if not name.endswith(RIG_SET_SUFFIX):
        tokens = name.split('_')
        if len(tokens) == 4:
            tokens[3] = RIG_SET_SUFFIX
            name = '_'.join(tokens)
        elif name.endswith('_'):
            name = name + RIG_SET_SUFFIX
        else:
            name = f'{name}_{RIG_SET_SUFFIX}'
    return name


def create_rigset(name, parent=None):
    """ Create an empty set with namespace RIG_SET_NAMESPACE.
        :param name: the sets name
        :param parent: The set in which the new set should be created, usually the rigset module's parent set.
        :return: the set
    """
    if parent and '_' not in name:
        side, mod, _, _ = parent.split('_')
        name = f'{side}_{mod}_{name}'
    name = force_rigset_suffix(name)
    if pm.objExists(name):
        raise errorutl.RbkNotUnique(f'A set with the name "{name}" exists already.')
    rigset = pm.sets(empty=True, name=name)
    if parent:
        if not pm.objExists(parent):
            raise errorutl.RbkNotFound(f'Given parent set does not exist: "{parent}"')
        add_to_set(parent, rigset)
    return rigset


def get_all_rigsets():
    """ Get all rigging sets in the current scene.
        :return: list of sets
    """
    return pm.ls(f'?_*_{RIG_SET_SUFFIX}', type='objectSet')


def get_inactive_members(s):
    """ Get all the objects/component names that were published with the set but are not yet in
        the set. Those objects are stored in the notes attribute.
        :param s: the sets name
        :return: list of objects/components that are stored in the notes attribute
    """
    s = force_rigset_suffix(s)
    inactive = []
    try:
        inactive = pm.getAttr(f'{s}.notes').split('\n')[1:]
    except pm.general.MayaAttributeError:
        # no notes stored on the given set
        inactive = []
    finally:
        if inactive == [u'']:
            # Note exists but no inactive objects stored
            inactive = []
    return inactive


def get_active_members(s):
    """ Get the objects/components that are currently in the set.
        Update before so no existing objects are skipped.
        :param s: the sets name
    """
    s = force_rigset_suffix(s)
    return pm.sets(s, q=True) or []


def update_members(s):
    """ Try to add the inactive set members to the set.
        :param s: the sets name
        :return: list of objects/components that are still inactive.

        :attention: The members should usually stay inactive during the rigBuild!
                    This is because we probably call the load function at start of the rigBuild
                    where not all objects exist. Adding only parts of the members to the active
                    objects would mess with the order. So we add everything as inactive first, then
                    the user can make the sets active when everything is in place.
                    Also when we duplicate meshes during the rigBuild, the duplicates of active
                    members will end up in the set, which is usually not intended. So keeping the
                    sets inactive until the rigBuild has finished is a good idea.
    """
    s = force_rigset_suffix(s)
    inactive = get_inactive_members(s)
    if not inactive:
        return []
    cannot_update = add_to_set(s, inactive)
    if cannot_update:
        print(f'Some objects from "{s}" are inactive in the scene.\nInactive Objects:\n')
        for cu in cannot_update:
            print(cu)
    add_inactive_members_to_notes(s, cannot_update, overwrite=True)
    return cannot_update


def update_all_nested_sets():
    """ Update all sets that have only other rig sets as members.

        This will leave all members that are not sets inactive, so we avoid all the troubles of
        having active members but can still have a cleaner outliner.
    """
    for s in get_all_rigsets():
        members = get_all_members(s)
        for m in members:
            if not pm.objExists(m) or pm.objectType(m) != 'objectSet':
                break
        else:
            update_members(s)


def update_all_rigsets():
    """ Call updateMembers for all existing rig sets
        :return: list of objects/components that are still inactive.
    """
    cannot_update = []
    for s in get_all_rigsets():
        cannot_update += update_members(s)
    return cannot_update


def make_all_members_inactive(s):
    """ Add all set members to the inactive objects list and remove all active objects from
        the set.
    """
    s = force_rigset_suffix(s)
    members = get_all_members(s)
    add_inactive_members_to_notes(s, members, overwrite=False)
    pm.sets(s, clear=True)


def add_inactive_members_to_notes(s, inactive, overwrite=True):
    """ Store the given objects/components in the notes attribute of the set.
        :param s: the sets name
        :param inactive: list of inactive objects/components
        :param overwrite: True  - Ignore existing inactive objects and add only the ones in the
                                  'inactive' list to the notes.
                          False - Keep the existing inactive objects append the given objects.
    """
    s = force_rigset_suffix(s)
    inactive = [str(a) for a in inactive]
    notes = attrutl.add_string(s, 'notes')
    notes.set(l=False)
    if overwrite:
        inactive_string = 'Inactive objects/components: \n' + '\n'.join(inactive)
    else:
        existing_inactive = [a for a in get_inactive_members(s) if a not in inactive]
        inactive_string = 'Inactive objects/components: \n' + '\n'.join(existing_inactive + inactive)
    pm.setAttr(f'{s}.notes', inactive_string, type='string')


def get_active_and_inactive_members(s):
    """ Get the active set members and the inactive ones.
        :param s: the sets name
        :return: (activeMembers, inactive)
    """
    active = get_active_members(s)
    inactive = get_inactive_members(s)
    return pymelutl.to_pynode(active), pymelutl.to_pynode(inactive)


def get_all_members(s):
    """ Get all members of the given set. This does not differentiate between active and
        inactive members.
        :param s: the sets name
        :return: all members as list
    """
    active, inactive = get_active_and_inactive_members(s)
    return pymelutl.to_pynode(active + inactive)


def get_all_members_recursive(s, exclude_sets=True):
    """ Same as getAllMembers, but if a member is a rigset itself, get its members as well.
        :param s: the sets name
        :param exclude_sets: only return 'real' members, not other sets.
        :return: all members as list
    """
    all_members = []

    def get_members(current_set, output=all_members):
        current_members = get_all_members(current_set)
        for cm in current_members:
            if cm.endswith(RIG_SET_SUFFIX):
                get_members(cm)
            else:
                output.append(cm)
            if not exclude_sets and current_set != s:
                output.append(current_set)
    get_members(s, all_members)
    return pymelutl.to_pynode(all_members)


def add_to_set(s, members, add_as_active=True):
    """ Add the given members to the set if they exist, otherwise store them in the notes.
        :param s: the sets name
        :param members: list of objects/components
        :param add_as_active: Add the given objects as active members of the set if possible.
    """
    pm.select(cl=True)  # somehow selected objects get added sometimes, brute force for now
    s = force_rigset_suffix(s)
    if add_as_active:
        cannot_add = []
        try:
            # Try to add all at once first. If all objects exist this is a lot faster.
            pm.sets(s, e=True, add=members)
        except pm.general.MayaNodeError:
            for m in members:
                if pm.objExists(m):
                    pm.sets(s, e=True, add=m)
                else:
                    cannot_add.append(m)
    else:
        cannot_add = members

    add_inactive_members_to_notes(s, cannot_add, overwrite=False)
    return cannot_add


def create_rigsets_from_dict(d):
    """ Create rigging sets from the dict that is published to the json file.
        The exported dict structure is like:
        {
        "C_mod_my_RIGSET": [u"C_someObj_PLY"],
        "C_mod_myOther_RIGSET": [u"C_stuff_PLY", u"C_blah_PLY"]
        }

        :attention: The members are always loaded as inactive! This is because we probably call
                    the load function at start of the rig build where not all objects exist. Adding
                    only parts of the members to the active objects would mess with the order. So
                    we add everything as inactive first, then the user can make the sets active
                    when everything is in place.
                    Also, when we duplicate meshes during the rigBuild, the duplicates of active
                    members will end up in the set, which is usually not intended. So keeping the
                    sets inactive until the rigBuild has finished is a good idea.
                    The one exception to this are nested sets. We can safely update them right
                    away, since we know all sets exist and there's no point in duplicating a set.

        :param d: the dict
    """
    for name, members in d.items():
        s = create_rigset(name)
        add_to_set(s, members, add_as_active=False)
    update_all_nested_sets()
