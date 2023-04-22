# rigbaukasten
fully procedural modular auto rigging system for Maya


## Welcome

Rigbaukasten is a system for creating animation rigs in maya using python (pymel). 
At the moment the main focus is biped rigging, though it can be used for 
other characters/vehicles/props due to its modular nature.

## Installation

After cloning/downloading rigbaukasten, first make sure the root directory 'rigbaukasten3' 
is available in mayas PYTHONPATH. 
See [Maya Help - Scripting - Python - Use external libraries](https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=GUID-C24973A1-F6BF-4614-BC3A-9F1A51D78F4C) 
if you're unsure how to accomplish that.

Next you have to build the rigbaukasten menu by running this:
```py
from rigbaukasten import rbk_startup
rbk_startup.main()
```
If you want to add this to your `userSetup.py` you should wrap the call 
with `maya.utils.executeDeferred` to make sure the main menu bar already exists when 
running the command.

```py
from maya import utils
from rigbaukasten import rbk_startup
utils.executeDeferred(rbk_startup.main)
```

## Setting up the environment

Rigbaukasten uses a custom environment object (`rigbaukasten.environment`) to interact with 
the file system. This object is the interface that lets the system know where the model is, 
where to save its data, where to find the rig build scripts, (...). 
To make this work in your maya project, you can either **mimic my default file structure** or 
**modify the environment utility**.

### Mimic the default structure

The default structure is based on the maya project folder (File - Set Project). Inside the 
project folder there are three folders for asset types (props, vehicles & characters). Inside 
those there is a folder for each asset, containing a model folder with .ma files and the 
following naming convention: `<asset_name>_model_v<3 digit version number>`.

In a tree view this would be:
```
├── maya_project_folder
    ├── characters
    │   ├── <asset_name>
    │       ├── model
    │           ├── <asset_name>_model_v<version>.ma
    ├── vehicles
    ├── props
    ├── workspace.mel
```
and a concreate example could be
```
├── theDarkKnight
    ├── characters
    │   ├── batman
    │       ├── model
    │           ├── batman_model_v001.ma
    ├── vehicles
    │   ├── batmobile
    │       ├── model
    │           ├── batmobile_model_v001.ma
    ├── props
    │   ├── batarang
    │       ├── model
    │           ├── batarang_model_v001.ma
    ├── workspace.mel
```

### Modifying the environment utility

If you already have a structure for your files, or are using some kind of pipeline tool that 
manages the file system, you have to modify `rigbaukasten.utils.environmentutl`. This python 
module contains a template class (`AbstractEnvironment`) that needs to be overwritten with 
a concrete implementation (`Environment`). You can overwrite the concrete implementation
however needed. It only needs to obey the structure from the abstract class. Practically 
that means your custom implementation must:
 * be available as `rigbaukasten.utils.environmentutl.Environment`
 * inherit from `rigbaukasten.utils.environmentutl.AbstractEnvironment`
 * implement all abstract methods, so that:
   * `get_asset_name()` returns a string with the name of the current asset
   * `get_model_path()` returns the file path (string) to the model
   * `get_rigdata_path()` retuns a file path (string) to where rigbaukasten can write rig data per asset
   * `get_rig_builds_path()` returns a file path(string) where rigbaukasten can store the rig build scripts
   * `get_resources_path()` returns the path to the resources folder (string). This can probably be
     copied from the default implementation in most cases. Only change this if you already have a
     resources folder in your system and don't want to have a separate one here.
   * `set()` can be called to make all the above work.
