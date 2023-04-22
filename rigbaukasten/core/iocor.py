import json
import os
import pymel.core as pm

import rigbaukasten
from rigbaukasten.library import controllib, guidelib, skinlib, rigsetlib
from rigbaukasten.utils import errorutl, ioutl, pymelutl, constraintutl


class BaseIo(object):
    def __init__(self, module_key):
        self.module_key = module_key

    def get_latest_folder(self, io_type='ctls'):
        module_folder = os.path.join(rigbaukasten.environment.get_rigdata_path(), self.module_key)
        return ioutl.get_latest_folder(module_folder, file_prefix=f'{io_type}_v')

    def make_next_folder(self, io_type='ctls'):
        module_folder = os.path.join(rigbaukasten.environment.get_rigdata_path(), self.module_key)
        if not os.path.exists(module_folder):
            os.makedirs(module_folder)
        versions = [a for a in os.listdir(module_folder) if a.startswith(f'{io_type}_v')]
        if versions:
            versions.sort()
            latest_version = int(versions[-1].replace(f'{io_type}_v', ''))
            next_version = latest_version + 1
        else:
            next_version = 1
        next_folder = os.path.join(module_folder, f'{io_type}_v{next_version:03d}')
        os.mkdir(next_folder)
        return next_folder

    def write_single_json(self, data, io_type='ctls'):
        """ Write the given data to a single json file in a new up-versioned folder. """
        publish_folder = self.make_next_folder(io_type=io_type)
        publish_file = os.path.join(publish_folder, f'{self.module_key}_{io_type}.json')
        with open(publish_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f'SUCCESS! Published {io_type} to {publish_file}')
        return publish_file

    def read_single_json(self, io_type='ctls'):
        """ Read the data from the last exported rigdata folder. """
        load_folder = self.get_latest_folder(io_type=io_type)
        if not load_folder:
            return None  # no data of given io_type exists

        load_file = os.path.join(load_folder, f'{self.module_key}_{io_type}.json')
        with open(load_file, 'r') as f:
            data = json.load(f)
        return data


class RigDataIo(BaseIo):
    def __init__(self, module_key):
        super().__init__(module_key)

        self.publishers = {
            'ctls': self.publish_ctls,
            'constraints': self.publish_constraints,
            'guides': self.publish_guides,
            'skinClusters': self.publish_skins,
            'blendshapes': self.publish_blendshapes,
            'rigsets': self.publish_rigsets,
            'drivenKeys': self.publish_driven_keys
        }

        self.loaders = {
            'ctls': self.load_ctls,
            'constraints': self.load_constraints,
            'guides': self.load_guides,
            'skinClusters': self.load_skins,
            'blendshapes': self.load_blendshapes,
            'rigsets': self.load_rigsets,
            'drivenKeys': self.load_driven_keys
        }

    def publish_rigdata(self, io_type, nodes):
        if nodes:
            publisher = self.publishers[io_type]
            return publisher(nodes)

    def load_rigdata(self, io_type):
        loader = self.loaders[io_type]
        return loader()

    def publish_ctls(self, ctls):
        data = {}
        for ctl in ctls:
            data[ctl.name()] = controllib.get_ctl_shape_data(ctl)

        return self.write_single_json(data, io_type='ctls')
        # publish_folder = self.make_next_folder(io_type='ctls')
        # publish_file = os.path.join(publish_folder, f'{self.module_key}_ctls.json')
        # with open(publish_file, 'w') as f:
        #     json.dump(data, f, indent=4)
        # print(f'SUCCESS! Published ctls to {publish_file}')
        # return publish_file

    def load_ctls(self):
        data = self.read_single_json(io_type='ctls')
        if data is None:
            return
        # load_folder = self.get_latest_folder(io_type='ctls')
        # if not load_folder:
        #     return
        # load_file = os.path.join(load_folder, f'{self.module_key}_ctls.json')
        #
        # with open(load_file, 'r') as f:
        #     data = json.load(f)

        for ctl_name, settings in data.items():
            if pm.objExists(ctl_name):
                ctl = pm.PyNode(ctl_name)
                controllib.set_ctl_shape_data(ctl=ctl, data=settings)
            else:
                print(f'{ctl_name} not found during ctl shape import, skipping...')

    def publish_constraints(self, grp):
        """ Publish all constraints inside the given group. """
        constraints = pm.listRelatives(grp, type='constraint', ad=True) or []
        data = constraintutl.get_constraint_data(constraints)
        data = pymelutl.to_str(data)
        self.write_single_json(data, io_type='constraints')

    def load_constraints(self):
        data = self.read_single_json(io_type='constraints')
        if data is None:
            return
        constraintutl.create_constraints_from_data(data)

    def publish_rigsets(self, parent_set):
        parent_set = parent_set[0]
        children, inactive = rigsetlib.get_active_and_inactive_members(parent_set)
        child_sets, child_objs = [], []
        for c in children:
            if pm.objectType(c) == 'objectSet':
                child_sets.append(c)
            else:
                child_objs.append(c)
        if child_objs:
            raise errorutl.RbkValueError(
                'Objects in a parent set are not allowed! Only rigsets can be nested in the parent rigset. '
                f'Remove the following objects from "{parent_set}": {child_objs}'
            )
        if inactive:
            raise errorutl.RbkValueError(
                'Inactive objects are not allowed in a parent rigset. '
                f'Remove the following inactive objects from "{parent_set}": {inactive}'
            )
        if not child_sets:
            return

        all_members = rigsetlib.get_all_members_recursive(parent_set, exclude_sets=False)
        export_sets = [a for a in all_members if pm.objectType(a) == 'objectSet']
        export_sets.append(parent_set)

        publish_folder = self.make_next_folder(io_type='rigsets')
        publish_files = []
        for es in export_sets:
            set_members = pymelutl.to_str(rigsetlib.get_all_members(es))

            publish_file = os.path.join(publish_folder, f'{es}.json')
            with open(publish_file, 'w') as f:
                json.dump(set_members, f, indent=4)
            publish_files.append([publish_file])
        print(f'SUCCESS! Published rigsets to {publish_folder}')
        return publish_files

    def load_rigsets(self):
        load_folder = self.get_latest_folder(io_type='rigsets')
        if not load_folder:
            return
        load_files = os.listdir(load_folder)
        data = {}
        for lf in load_files:
            load_path = os.path.join(load_folder, lf)
            set_name = lf.replace('.json', '')
            with open(load_path, 'r') as f:
                data[set_name] = json.load(f)
        rigsetlib.create_rigsets_from_dict(data)

    def publish_guides(self, guides):
        data = {}
        for gde in guides:
            data[gde.name()] = guidelib.get_guide_data(gde)

        return self.write_single_json(data, io_type='guides')
        # publish_folder = self.make_next_folder(io_type='guides')
        # publish_file = os.path.join(publish_folder, f'{self.module_key}_guides.json')
        # with open(publish_file, 'w') as f:
        #     json.dump(data, f, indent=4)
        # print(f'SUCCESS! Pubished guides to {publish_file}')
        # return publish_file

    def load_guides(self):
        data = self.read_single_json(io_type='guides')
        if data is None:
            return
        # load_folder = self.get_latest_folder(io_type='guides')
        # if not load_folder:
        #     return
        # load_file = os.path.join(load_folder, f'{self.module_key}_guides.json')
        #
        # with open(load_file, 'r') as f:
        #     data = json.load(f)

        for gde_name, settings in data.items():
            if pm.objExists(gde_name):
                gde = pm.PyNode(gde_name)
                guidelib.set_guide_data(gde=gde, data=settings)
            else:
                print(f'{gde_name} not found during guide import, skipping...')

    def publish_skins(self, skins):
        publish_folder = self.make_next_folder(io_type='skinClusters')
        publish_files = []
        for skin in skins:
            publish_file = f'{self.module_key}_skinClusters.{skin}.json'
            pm.deformerWeights(
                publish_file,
                path=publish_folder,
                ex=True,
                df=skin,
                skip=f'?!{skin}',
                weightPrecision=5,
                weightTolerance=0.0001
            )
            publish_files.append(publish_file)
        print(f'SUCCESS! Published skinClusters to {publish_folder}')
        return publish_files

    def load_skins(self):
        load_folder = self.get_latest_folder(io_type='skinClusters')
        if not load_folder:
            return
        load_files = [j for j in os.listdir(load_folder) if self.module_key in j and j.endswith('.json')]

        skins = []
        for load_file in load_files:
            with open(os.path.join(load_folder, load_file), 'r') as f:
                data = json.load(f)
            try:
                skn = skinlib.create_skin_from_data(data)
                skins.append(skn)
            except errorutl.RbkNotFound:
                print(f'Geo not found during skin weight import, skipping: {load_file}')
        return skins

    def publish_blendshapes(self, blendshapes):
        publish_folder = self.make_next_folder(io_type='blendshapes')
        publish_files = []
        for bs in blendshapes:
            publish_file = f'{self.module_key}_blendshapes.{bs}.shp'
            publish_path = os.path.join(publish_folder, publish_file)
            pm.blendShape(bs, e=True, export=publish_path)
            publish_files.append(publish_file)
        print(f'SUCCESS! Published blendshapes to {publish_folder}')
        return publish_files

    def load_blendshapes(self):
        load_folder = self.get_latest_folder(io_type='blendshapes')
        if not load_folder:
            return
        load_files = [j for j in os.listdir(load_folder) if self.module_key in j and j.endswith('.shp')]

        for load_file in load_files:
            bs = load_file.split('.')[1]
            if pm.objExists(bs):
                pm.blendShape(bs, e=True, ip=os.path.join(load_folder, load_file))
            else:
                print(f'BlendShape not found during blendshape import, skipping: {load_file}')

    def publish_driven_keys(self, driven_nodes):
        """
        Publish driven keys as rigdata.
        Find all driven keys (animCurve nodes) that are driving the given 'driven nodes' and export them as mayaAscii.
        :param driven_nodes: Nodes that have channels driven by a drivenKey
        """
        anim_crvs = []
        for d in driven_nodes:
            for anim_crv in pm.listConnections(d, s=True, d=False, type='animCurve'):
                driver_plug = pm.listConnections(f'{anim_crv}.i', p=True, s=True, d=False)
                if driver_plug:
                    anim_crvs.append(anim_crv)

        publish_folder = self.make_next_folder(io_type='drivenKeys')
        publish_file = f'{self.module_key}_drivenKeys.ma'
        publish_path = os.path.join(publish_folder, publish_file)
        pm.select(anim_crvs, r=True)
        pm.exportSelected(publish_path, constructionHistory=False)
        print(f'SUCCESS! Published drivenKeys to {publish_file}')
        return publish_file

    def load_driven_keys(self):
        """
        Load Driven keys as rigdata.
        Import the latest drivenKeys file with a prefix. Then find the matching existing non-prefixed drivenKey node
        in the scene and replace it with the imported one.
        """
        load_folder = self.get_latest_folder(io_type='drivenKeys')
        if not load_folder:
            return
        load_file = os.path.join(load_folder, f'{self.module_key}_drivenKeys.ma')

        prefix = 'drivenKeyImportTmp_'
        pm.importFile(load_file, renameAll=True, renamingPrefix=prefix)
        nodes = pm.ls(f'{prefix}_*')
        junk = []
        for node in nodes:
            if not pm.objectType(node, isAType='animCurve'):
                pm.warning(f'Removing invalid node {node} from {load_file} - not an animCurve!')
                junk.append(node)
                continue
            swap_name = node.replace(f'{prefix}_', '')
            if not pm.objExists(swap_name):
                pm.warning(f'Removing invalid node {node} from {load_file} - no matching driven key in current scene!')
                junk.append(node)
                continue
            swap_node = pm.PyNode(swap_name)
            input_connections = pm.listConnections(swap_node.i, p=True, s=True, d=False)
            output_connections = pm.listConnections(swap_node.o, p=True, d=True, s=False)
            if not input_connections:
                pm.warning(f'Removing invalid node {node} from {load_file} - matching anim curve is not a driven key!')
                junk.append(node)
                continue
            input_connections[0].connect(node.i, force=True)
            for o in output_connections:
                node.o.connect(o, force=True)
            pm.delete(swap_node)
            node.rename(swap_name)
        if junk:
            pm.delete(junk)
