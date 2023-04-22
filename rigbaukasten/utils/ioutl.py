import os


def get_latest_folder(folder, file_prefix=None):
    if not os.path.exists(folder):
        return None
    versions = os.listdir(folder)
    if file_prefix:
        versions = [a for a in versions if a.startswith(file_prefix)]
    if not versions:
        return None
    versions.sort()
    latest = os.path.join(folder, versions[-1])
    return latest
