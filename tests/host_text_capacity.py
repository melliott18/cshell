#!/usr/bin/env python3
"""Run text qualification with a private Darwin FAT12 ENOSPC filesystem."""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile


def run(binary, path, record, audit=False):
    if platform.system() != 'Darwin':
        raise RuntimeError('Darwin disk-image fixture requires macOS; Linux uses Docker tmpfs')
    # Keep a failed-to-detach mount and its image intact; never recursively
    # remove a directory that might still be mounted.
    record.parent.mkdir(parents=True,exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='csh-text-capacity-',dir=record.parent.resolve()))
    root.chmod(0o755)
    mount = root/'mount'; mount.mkdir()
    image = root/'capacity.dmg'
    metadata = dict(root=str(root), image=str(image), mount=str(mount), detached=False)
    device = None
    attach_attempted = False
    attachment_known = True
    status = 1
    try:
        created = subprocess.run(['hdiutil','create','-size','1440k','-fs','MS-DOS',
            '-volname','CSH73CAP','-layout','NONE',str(image)],capture_output=True,check=True,timeout=30)
        metadata['create_stdout'] = created.stdout.decode()
        attach_attempted = True
        attachment_known = False
        attached = subprocess.run(['hdiutil','attach','-nobrowse','-mountpoint',str(mount),
                                   '-plist',str(image)],capture_output=True,check=True,timeout=30)
        metadata['attachment'] = plistlib.loads(attached.stdout)
        entities = metadata['attachment']['system-entities']
        mounted = [e for e in entities if e.get('mount-point') == str(mount)]
        if len(mounted) != 1:
            raise RuntimeError('Expected one private mounted filesystem')
        device = mounted[0]['dev-entry']
        attachment_known = True
        info=os.statvfs(mount)
        metadata['filesystem_bytes']=info.f_blocks*info.f_frsize
        if metadata['filesystem_bytes'] > 2*1024*1024 or not os.path.ismount(mount):
            raise RuntimeError('Disk image is not the dedicated <=2 MiB filesystem')
        command=[sys.executable,str(Path(__file__).with_name('host_text.py')),
                 str(binary.resolve()),'--path',path,'--boundaries','--capacity-root',str(mount),
                 '--record',str(record.resolve())]
        if audit: command.append('--audit')
        metadata['command']=command
        status=subprocess.run(command,timeout=300).returncode
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        metadata['error']=str(error)
        if isinstance(error,subprocess.CalledProcessError):
            metadata['stderr']=(error.stderr or b'').decode(errors='replace')
    finally:
        # A timed-out attach can leave an unmounted image device behind.
        # Query only this exact image identity before deciding it is removed.
        if attach_attempted and not attachment_known:
            try:
                info=subprocess.run(['hdiutil','info','-plist'],capture_output=True,check=True,timeout=10)
                attached_images=[item for item in plistlib.loads(info.stdout).get('images',[])
                                 if item.get('image-path') == str(image)]
                if attached_images:
                    device=next(entity['dev-entry'] for entity in attached_images[0]['system-entities']
                                if 'dev-entry' in entity)
                attachment_known=True
            except (OSError,ValueError,KeyError,StopIteration,subprocess.SubprocessError) as error:
                metadata['attachment_query_error']=str(error)
        if device or os.path.ismount(mount):
            try:
                subprocess.run(['hdiutil','detach',device or str(mount)],capture_output=True,check=True,timeout=15)
                metadata['detached']=not os.path.ismount(mount)
            except (OSError,subprocess.SubprocessError) as error:
                metadata['detach_error']=str(error);status=1
        elif attachment_known:
            metadata['detached']=True
        if metadata['detached']:
            try:
                if image.exists(): image.unlink()
                mount.rmdir();root.rmdir()
            except OSError as error:
                metadata['cleanup_error']=str(error);status=1
        else:
            status=1
        metadata['fixture_removed']=not root.exists()
        record.parent.mkdir(parents=True,exist_ok=True)
        record.with_suffix('.capacity.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return status


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary',type=Path)
    parser.add_argument('--path',default=os.defpath)
    parser.add_argument('--record',type=Path,required=True)
    parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    raise SystemExit(run(args.binary,args.path,args.record,args.audit))
