"""Measured optional Office engine; only owned clean projections are opened."""
import os,shutil,subprocess,xml.etree.ElementTree as E
from pathlib import Path
from sdk.cli.arc1cli.office_tables import sha

def probe():
    executable=shutil.which('soffice') or shutil.which('libreoffice')
    if not executable:return {'available':False,'state':'OFFICE_ENGINE_NOT_INSTALLED'}
    path=Path(executable).resolve();run=subprocess.run([str(path),'--version'],capture_output=True,text=True,timeout=15)
    if run.returncode:raise ValueError('OFFICE_ENGINE_VERSION_FAILED')
    version=run.stdout.strip()
    font=Path(__file__).resolve().parents[1]/'branding/fonts/NotoSansCJKsc-Regular.otf'
    return {'available':True,'executable':str(path),'launcher_sha256':sha(path.read_bytes()),'version':version,'development_build':any(s in version.lower() for s in ('alpha','beta','dev')),'font_assets':[{'name':font.name,'sha256':sha(font.read_bytes())}] if font.is_file() else []}
def font_config(folder):
    folder=Path(folder).resolve();folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    root=E.Element('fontconfig');base=os.environ.get('FONTCONFIG_FILE','/etc/fonts/fonts.conf')
    E.SubElement(root,'include',{'ignore_missing':'yes'}).text=base
    E.SubElement(root,'dir').text=str(Path(__file__).resolve().parents[1]/'branding/fonts')
    E.SubElement(root,'cachedir').text=str(folder/'font-cache')
    target=folder/'fonts.conf';E.ElementTree(root).write(target,encoding='utf-8',xml_declaration=True);return target
def profile(folder):
    folder=Path(folder);folder.mkdir(mode=0o700,parents=True,exist_ok=True);(folder/'user').mkdir(mode=0o700,exist_ok=True)
    (folder/'user/registrymodifications.xcu').write_text('''<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop><prop oor:name="SecureURL" oor:op="fuse"><value/></prop></item></oor:items>''')
    return folder.resolve().as_uri()
def convert(source,destination,fmt,kind='document',timeout=150):
    source=Path(source).resolve();destination=Path(destination).resolve();destination.mkdir(mode=0o700,parents=True,exist_ok=True)
    before=probe()
    if not before['available']:raise ValueError('OFFICE_ENGINE_NOT_INSTALLED')
    filters={'ods':'calc8','xlsx':'Calc MS Excel 2007 XML','docx':'Office Open XML Text','pdf':'calc_pdf_Export' if kind=='table' else 'writer_pdf_Export'}
    if fmt not in filters:raise ValueError('OFFICE_CONVERSION_FORMAT')
    target=destination/(source.stem+'.'+fmt)
    if target.exists() or target==source:raise ValueError('OFFICE_CONVERSION_DESTINATION_EXISTS')
    original=sha(source.read_bytes());uri=profile(destination.parent/('profile-'+fmt));command=[before['executable'],'-env:UserInstallation='+uri,'--headless','--nologo','--nodefault','--norestore','--nofirststartwizard','--convert-to',fmt+':'+filters[fmt],'--outdir',str(destination),str(source)]
    env={**os.environ,'FONTCONFIG_FILE':str(font_config(destination.parent))}
    run=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout,env=env)
    if run.returncode or not target.is_file() or not target.stat().st_size:raise ValueError('OFFICE_CONVERSION_FAILED:'+run.stderr[-800:])
    if target.stat().st_size>32*1024*1024:raise ValueError('OFFICE_CONVERSION_OUTPUT_LIMIT')
    if sha(source.read_bytes())!=original or probe()!=before:raise ValueError('OFFICE_INPUT_OR_ENGINE_CHANGED')
    return target,{'engine':before,'isolated_profile':True,'macro_security':'VERY_HIGH_EMPTY_TRUSTED_LOCATIONS','input_sha256':original,'output_sha256':sha(target.read_bytes()),'filter':filters[fmt]}
def editor_command(source,folder):
    before=probe()
    if not before['available']:raise ValueError('OFFICE_ENGINE_NOT_INSTALLED')
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):raise ValueError('OFFICE_EDITOR_DISPLAY_UNAVAILABLE: use the prepared candidate on the Debian desktop')
    uri=profile(Path(folder)/'editor-profile')
    return [before['executable'],'-env:UserInstallation='+uri,'--nologo','--norestore','--nofirststartwizard',str(Path(source).resolve())],{'FONTCONFIG_FILE':str(font_config(Path(folder)/'fonts'))}
