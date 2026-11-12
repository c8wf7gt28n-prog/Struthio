"""Reproducible console build/lifecycle targets over the shared kernel services."""
import argparse,json,time
from pathlib import Path
from . import record_io as io,console_build


def demo(root):
    from .engineering_kernel import Kernel,operator
    root=Path(root).resolve();report={'schema':'arc.virtual-console-lifecycle/1','status':'RUNNING','class':'HOST_SIM','physical_hardware':False,'board_boot_qualified':False,'cases':[],'created':time.time()}
    kernel=Kernel(root);owner=operator('console-lifecycle');session_id=None
    def call(op,args=None):
        r=kernel.dispatch(op,args or {},owner)
        if not r['ok']:raise ValueError(r['error']['message'])
        return r['result']
    def check(name,value):
        report['cases'].append({'name':name,'passed':bool(value)})
        if not value:raise ValueError('LIFECYCLE_CHECK_FAILED: '+name)
    def buttons(value=0,hat=8,ticks=1):return call('console.input',{'id':session_id,'buttons':value,'hat':hat,'ticks':ticks})
    def press(value=0,hat=8):
        buttons(value,hat);return buttons()
    try:
        built=console_build.build(root);report['revision']=built['revision'];report['input_hashes']=built['input_hashes']
        state=call('console.open');session_id=state['id'];check('resident NOR startup, device contracts and media discovery',state['frame']['screen']=='MENU' and state['frame']['card']==1 and state['metrics']['hub_ep0_requests']>0)
        names={row['event'] for row in state['trace']}
        check('canonical F133 producer and ARC-OS consumer exchange current boot info',{'F133_BOOT_INFORMATION','ARCOS_BOOT_INFORMATION'}<=names and state['metrics'].get('federation_ready_mask')==15)
        check('firmware AJOB crosses actual canonical 12F RTL and returns to C parser',state['metrics'].get('rtl_transactions')==1 and 'F133_12F_AJOB_RESULT' in names and any(r.get('class')=='RTL_SIM' for r in state['trace']))
        check('virtual parent reset and USB BOT block/FAT calls precede game admission',{'USB_HUB_CHILD_READY','USB_MEDIA_ENUMERATED','BOT_CBW','BOT_DATA','BOT_CSW','SCSI_READ10','FAT_MOUNT','FAT_OPEN_GAME_ARC','FAT_FILE_READ'}<=names and state['metrics'].get('usb_block_reads',0)>0)
        started=press(1);check('Start launches native C STRUTHIO' ,started['frame']['screen']=='GAME')
        moved=buttons(1,hat=2,ticks=30);check('logical controller changes native state and produces graphics',bool(moved['frame']['rects']) and moved['frame']['game_digest']!=started['frame']['game_digest'])
        check('game commands traverse the existing C graphics-link protocol',moved['metrics']['graphics_frames']>0 and moved['metrics']['graphics_packets']>2)
        report['game_frame']=moved['frame'];report['boot_trace']=state['trace']
        returned=press(256);check('safe return to ARC-OS menu',returned['frame']['screen']=='MENU')
        press(hat=4);ejected=press(1);check('Eject unmounts game media',not ejected['frame']['card'] and ejected['frame']['ejected'])
        call('console.media',{'id':session_id,'fixture':'normal'});press(hat=4);settings=press(1);check('Settings opens from approved menu',settings['frame']['screen']=='SETTINGS')
        changed=press(hat=2);check('Settings changes a bounded preference',changed['frame']['volume']==6)
        press(2);press(hat=4);off=buttons(1)
        check('Off closes the native process',off['frame']['screen']=='EXIT' and off['state']=='CLOSED');report['normal_session']=call('console.state',{'id':session_id});session_id=None
        bad=call('console.open',{'fixture':'corrupt'});session_id=bad['id'];denied=press(1);check('corrupt thumb drive is rejected and menu stays usable',bad['media']['error'].startswith('MEDIA_CORRUPT') and denied['frame']['screen']=='MENU' and not denied['frame']['card'])
        report['failure_session']=denied;call('console.close',{'id':session_id});session_id=None
        report['driver_failures']=[]
        for fixture,expected in [('bad_csw','USB_BOT_CSW_REJECTED'),('bad_fat','FAT_READ_FAILED'),('missing','MEDIA_UNAVAILABLE'),('incompatible','MEDIA_INCOMPATIBLE')]:
            bad=call('console.open',{'fixture':fixture});session_id=bad['id'];denied=press(1)
            check(fixture+' denies media while the menu remains usable',bad['media']['error'].startswith(expected) and denied['frame']['screen']=='MENU' and not denied['frame']['card'])
            if fixture=='bad_csw':check('bad CSW invokes reset and clear-halt recovery',any(x['event']=='BOT_RESET_RECOVERY' for x in bad['trace']))
            report['driver_failures'].append(bad);call('console.close',{'id':session_id});session_id=None
        report['participant_failures']=[]
        for fixture in ('stale_d213','reset_participant'):
            before=set((root/'.ledger/console').glob('*/state.json'))
            denied=kernel.dispatch('console.open',{'fixture':fixture},owner)
            after=set((root/'.ledger/console').glob('*/state.json'));added=after-before
            check(fixture+' blocks launcher admission',not denied['ok'] and len(added)==1)
            saved=io.strict_json(next(iter(added)).read_bytes());events=saved['trace']
            check(fixture+' records a failure and admits no media or game',not saved['frame'] and not any(x['event']=='FAT_OPEN_GAME_ARC' for x in events) and any(x['event']=='BOOT_REJECTED' for x in events))
            report['participant_failures'].append({'fixture':fixture,'api':denied,'record':saved})
        sample=call('console.open',{'fixture':'sample'});session_id=sample['id'];started=press(1)
        check('new SDK native starter loads from real FAT image through USB model',sample['game']['name']=='first_arc_game' and sample['frame']['card']==1 and started['frame']['screen']=='GAME')
        moved=buttons(0,hat=2,ticks=8)
        check('SDK sample accepts input and draws',moved['frame']['rects'] and moved['frame']['game_digest']!=started['frame']['game_digest'])
        returned=press(2);check('SDK sample returns safely with B',returned['frame']['screen']=='MENU')
        report['sdk_sample_session']=moved;call('console.close',{'id':session_id});session_id=None
        accepted=call('console.plan',{'path':console_build.OUT+'/virtual-probe.egon','profile':'egon-format-tool-limit'});check('offline eGON format plan accepted without a silicon claim',accepted['state']=='PLAN_ACCEPTED' and not accepted['board_boot_qualified'])
        rejected=kernel.dispatch('console.plan',{'path':console_build.OUT+'/arc_console_host','profile':'qemu-virt-rv64-existing'},owner);check('incompatible native-host image rejected',not rejected['ok'])
        blocked=call('console.plan',{'path':console_build.OUT+'/virtual-probe.egon','profile':'r10-f133-board'});check('unknown physical target binding remains blocked',blocked['state']=='BLOCKED' and not blocked['physical_write_enabled'])
        report['offline_plan']=accepted;report['rejected_plan']=rejected;report['board_plan']=blocked;report['status']='PASS'
    except (OSError,ValueError) as exc:report.update(status='FAIL',error=str(exc))
    finally:
        if session_id:kernel.dispatch('console.close',{'id':session_id},owner)
    report['finished']=time.time();io.write_json(root/console_build.OUT/'lifecycle.json',report);return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','demo']);parser.add_argument('--root',required=True,type=Path);a=parser.parse_args()
    try:r=console_build.build(a.root) if a.action=='build' else demo(a.root)
    except (OSError,ValueError) as exc:r={'status':'FAIL','error':str(exc)}
    print(json.dumps(r));return 0 if r['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
