from rigbaukasten.core import modulecor
import pymel.core as pm

from rigbaukasten.library import skinlib, rigsetlib
from rigbaukasten.utils import errorutl, pythonutl
from rigbaukasten.utils.typesutl import Jnt


class SimpleSkin(modulecor.RigModule):
    """ A simple skinCluster with given joints and geo. """
    def __init__(
            self,
            side,
            module_name,
            geo=(),
            joints=(),
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param geo: (PyNode, ) - Geo(s) that should get the skinCluster deformer assigned. If a group is given all
                    child nodes will be used.
        :param joints: (PyNode, ) or OutDataPointer(s) - Default joints for the skinClusters. More can of course be
                        added later in maya using 'Skin - Edit Influences - Add Influence'.
        """
        super().__init__(side=side, module_name=module_name)
        self.geo = pythonutl.force_list(geo)
        self.joints = joints if isinstance(joints, (list, tuple)) else [joints]

        self.skinClusters = []

    def get_child_geos(self):
        """ If self.geo contains groups, use their child meshes instead. """
        new_geo = []
        for geo in self.geo:
            immediate_shapes = pm.listRelatives(geo, shapes=True)
            if immediate_shapes:
                new_geo.append(geo)
                continue
            all_shapes = pm.listRelatives(geo, shapes=True, ad=True)
            for shape in all_shapes:
                trn = pm.listRelatives(shape, p=True)[0]
                if trn not in new_geo:
                    new_geo.append(trn)
        self.geo = new_geo

    def create_skins(self):
        joints = []
        for j in self.joints:
            if isinstance(j, Jnt):
                joints.append(self.get_output_data(j))
            elif pm.objExists(j):
                joints.append(j)
            else:
                raise errorutl.RbkValueError(
                    f"'joints' must be given as joint names or typesutl.Jnt pointers, not {type(j)}: ({j})"
                )
        for geo in self.geo:
            skn = skinlib.create_skin(side=self.side, module_name=self.module_name, joints=joints, geo=geo)
            self.skinClusters.append(skn)
        self.publish_nodes['skinClusters'] += self.skinClusters

    def deform_build(self):
        super().deform_build()
        self.get_child_geos()
        self.create_skins()

    def deform_connect(self):
        super().deform_connect()
        self.load_rigdata('skinClusters', False)


class SkinSet(SimpleSkin):
    """ Same as SimpleSkin, but geo is passed in via rig sets instead of names. """
    def __init__(
            self,
            side,
            module_name,
            joints=(),
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param joints: (PyNode, ) or OutDataPointer(s) - Default joints for the skinClusters. More can of course be
                        added later in maya using 'Skin - Edit Influences - Add Influence'.
        """
        super().__init__(side=side, module_name=module_name, joints=joints)

        self.load_rigdata(io_type='rigsets', recursive=False)
        parent_set_name = self.mk('parent_RIGSET')
        if pm.objExists(parent_set_name):
            # parent set was already created by load_rigdata()
            self.parent_set = pm.PyNode(parent_set_name)
        else:
            self.parent_set = rigsetlib.create_rigset(parent_set_name)
        self.publish_nodes['rigsets'].append(self.parent_set)
        geo_set_name = self.mk('geo_RIGSET')
        if pm.objExists(geo_set_name):
            # geo set was already created by load_rigdata()
            self.geo_set = pm.PyNode(geo_set_name)
        else:
            self.geo_set = rigsetlib.create_rigset(geo_set_name)
            pm.sets(self.parent_set, e=True, add=self.geo_set)

    def update_geo_from_set(self):
        """ Update self.geo with the objects from the set. """
        self.geo = rigsetlib.get_all_members(self.geo_set)
        if not self.geo:
            raise errorutl.RbkNotFound(f'No objects found in set: {self.geo_set}')

    def deform_build(self):
        self.update_geo_from_set()
        super().deform_build()


class TransferredSkin(modulecor.RigModule):
    """
    Create skinClusters based on already existing ones. E.g. to transfer skinning from lowRes to hiRes meshes.
    Specify source and target meshes by using sets with matching names and a 'Src_RIGSET' / 'Tgt_RIGSET' suffix.
    """
    def __init__(
            self,
            side='C',
            module_name='transferredSkin',
            uv_based=False
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param uv_based: bool - Transfer weights based on UVs. If False, closest point will be used.
        """
        super().__init__(side=side, module_name=module_name)
        self.side = side
        self.module_name = module_name
        self.uv_based = uv_based

        self.src_sets = []
        self.tgt_sets = []
        self.skin_clusters = []

        self.load_rigdata(io_type='rigsets', recursive=False)
        parent_set_name = self.mk('parent_RIGSET')
        if pm.objExists(parent_set_name):
            # parent set was already created by load_rigdata()
            self.parent_set = pm.PyNode(parent_set_name)
        else:
            self.parent_set = rigsetlib.create_rigset(parent_set_name)
        self.publish_nodes['rigsets'].append(self.parent_set)

    def get_sets(self):
        """ Get the source and target sets that the user has populated by now. """
        all_sets = rigsetlib.get_all_members(self.parent_set)
        invalid = []
        for s in all_sets:
            if s.name().endswith('Src_RIGSET'):
                self.src_sets.append(s)
            elif s.name().endswith('Tgt_RIGSET'):
                self.tgt_sets.append(s)
            else:
                invalid.append(s)
        if invalid:
            raise errorutl.RbkInvalidName(
                f'Invalid name for skin transfer sets, must end with "Src_RIGSET" or "Tgt_RIGSET". Got: {invalid}'
            )
        self.src_sets.sort()
        self.tgt_sets.sort()

    def create_target_skins(self):
        """ Pre-create the target skinClusters with the current joints of the source skinClusters.
            This is done, so we can create the skinClusters already in deform_build, and don't have to delay this
            'building' part until deform_connect. That way we have more control over the deformation order on the
            meshes, because we can control it by creating the RigModules in the according order.
        """
        src_jnts = None
        done = []
        for src_set, tgt_set in zip(self.src_sets, self.tgt_sets):
            for src in rigsetlib.get_all_members(src_set):
                try:
                    src_skin = skinlib.get_skin(src)
                except errorutl.RbkNotFound:
                    pass
                else:
                    src_jnts = src_skin.getInfluence()
                    break
            if src_jnts:
                for tgt in rigsetlib.get_all_members(tgt_set):
                    if isinstance(tgt, pm.general.Component):
                        tgt = tgt.node()
                    if tgt in done:
                        continue
                    skinlib.create_skin(side=self.side, module_name=self.module_name, joints=src_jnts, geo=tgt)
                    done.append(tgt)
                    if isinstance(tgt, pm.nt.Transform):
                        done.append(tgt.getShape())
                    if isinstance(tgt, pm.nt.Mesh):
                        done.append(tgt.getParent())

    def transfer_skins(self):
        """
        Now that the source skinClusters should have their weights, update the target influences and copy weights.
        """
        for src_set, tgt_set in zip(self.src_sets, self.tgt_sets):
            src = rigsetlib.get_all_members(src_set)
            tgt = rigsetlib.get_all_members(tgt_set)

            skinlib.transfer_skin(src, tgt, module_key=self.module_key, uv_based=self.uv_based)

    def deform_build(self):
        super().deform_build()
        self.get_sets()
        self.create_target_skins()

    def deform_connect(self):
        super().deform_connect()
        self.transfer_skins()
