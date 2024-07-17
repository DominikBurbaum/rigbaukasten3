import pymel.core as pm

from rigbaukasten.utils import attrutl


def fk_ik_snap_network_create(
        module_name,
        ik_ctls=(),
        ik_targets=(),
        fk_ctls=(),
        fk_targets=(),
        ik_set_attrs=None,
        fk_set_attrs=None
    ):
    network_node = pm.createNode('network', n=f'{module_name}_fkIkSnap_NET')
    for i, (ctl, tgt) in enumerate(zip(ik_ctls, ik_targets)):
        holder_plug = attrutl.add_message(network_node, f'snapToIk{i}')
        ctl_plug = attrutl.add_message(ctl, f'snapToIk{i}')
        tgt_plug = attrutl.add_message(tgt, f'snapToIk{i}')
        ctl_plug >> holder_plug
        holder_plug >> tgt_plug

    for i, (ctl, tgt) in enumerate(zip(fk_ctls, fk_targets)):
        holder_plug = attrutl.add_message(network_node, f'snapToFk{i}')
        ctl_plug = attrutl.add_message(ctl, f'snapToFk{i}')
        tgt_plug = attrutl.add_message(tgt, f'snapToFk{i}')
        ctl_plug >> holder_plug
        holder_plug >> tgt_plug

    for fkik, set_attrs in zip(['fk', 'ik'], [fk_set_attrs, ik_set_attrs]):
        if set_attrs and isinstance(set_attrs, dict):
            for val, plugs in set_attrs.items():
                val_str = str(val).replace('.', '_')
                val_plug = attrutl.add(network_node, f'{fkik}SetAttrTo{val_str}', 'double', default=val, multi=True)
                val_plug[0].set(val)
                for i, plug in enumerate(plugs):
                    plug >> val_plug[i + 1]

    attrutl.add_tag(network_node, 'fkIkSnapNetwork', module_name)


def fk_ik_snap_network_read(network_node):
    fk_snappers, ik_snappers = [], []
    fk_setters, ik_setters = {}, {}
    user_attrs = network_node.listAttr(ud=1)

    def source_and_target(plug_):
        return plug_.listConnections(s=True, d=False)[0], plug_.listConnections(s=False, d=True)[0]

    def value_and_plugs(plug_):
        val = plug_[0].get()
        size = plug_.get(size=True)
        return {val: [plug_[i].listConnections(s=True, d=False, p=True)[0] for i in range(1, size)]}

    for plug in sorted(user_attrs):
        attr_name = plug.attrName()
        if attr_name.startswith('snapToFk'):
            fk_snappers.append(source_and_target(plug))
        elif attr_name.startswith('snapToIk'):
            ik_snappers.append(source_and_target(plug))
        elif attr_name.startswith('fkSetAttrTo'):
            fk_setters.update(value_and_plugs(plug))
        elif attr_name.startswith('ikSetAttrTo'):
            ik_setters.update(value_and_plugs(plug))

    return {
        'to_fk_snap': fk_snappers,
        'to_fk_set': fk_setters,
        'to_ik_snap': ik_snappers,
        'to_ik_set': ik_setters,
    }


def fk_ik_snap(network_node, to_fk=True, set_key=True):
    data = fk_ik_snap_network_read(network_node)
    if to_fk:
        snappers = data['to_fk_snap']
        setters = data['to_fk_set']
    else:
        snappers = data['to_ik_snap']
        setters = data['to_ik_set']
    for val, plugs in setters.items():
        for plug in plugs:
            if plug.isFreeToChange() == 'notFreeToChange':
                pm.warning(f'Could not change {plug.name()} during fk ik snapping.')
                continue
            plug.set(val)
            if set_key:
                pm.setKeyframe(plug)
    for ctl, target in snappers:
        pm.matchTransform(ctl, target)
        if set_key:
            for attr_name in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz'):
                try:
                    pm.setKeyframe(ctl.attr(attr_name))
                except RuntimeError:
                    pass  # locked or connected, nevermind


def fk_ik_bake(network_nodes, to_fk=True, timerange=(), set_key=True):
    if not timerange:
        timerange = (pm.playbackOptions(q=1, min=1), pm.playbackOptions(q=1, max=1))
    for i in range(int(timerange[0]), int(timerange[1] + 1)):
        pm.currentTime(i)
        for network_node in network_nodes:
            fk_ik_snap(network_node=network_node, to_fk=to_fk, set_key=set_key)
