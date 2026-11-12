"""Portable, literal presentation of recorded console events (no timing model)."""
LABELS = {
    'RESET':'Reset entered', 'CLOCK_DDR':'Clock / memory fixture',
    'NOR_RESIDENT_CONTRACT':'Resident NOR contract',
    'F133_BOOT_INFORMATION':'F133 boot information',
    'ARCOS_BOOT_INFORMATION':'ARC-OS accepted boot information',
    'FAT_MOUNT':'Game filesystem mounted', 'FAT_OPEN_GAME_ARC':'GameCard opened',
    'USB_MEDIA_ENUMERATED':'USB media enumerated', 'MEDIA_DISCOVERY':'Game media discovery',
    'SCSI_READ10':'USB block read', 'FAT_FILE_READ':'Game bytes read',
    'FPGA12_RTL_EXCHANGE':'12F RTL transaction', 'ARCOS':'ARC-OS launcher',
    'BOOT_REJECTED':'Boot admission refused', 'BOT_RESET_RECOVERY':'USB recovery',
}
LANES = ('Boot / NOR', 'Federation', 'USB / media', 'ARC-OS / game')


def event_rows(trace, limit=2000):
    if not isinstance(trace,list) or type(limit) is not int or not 1<=limit<=2000:
        raise ValueError('EVENT_TRACE_BOUND')
    rows=[]
    for index, record in enumerate(trace[-limit:]):
        if not isinstance(record,dict):
            continue
        event=str(record.get('event','Unknown event'))
        if event.startswith(('USB','FAT','SCSI','BOT','MEDIA')):
            lane=2
        elif event.startswith(('FEDERATION','FPGA','D213')):
            lane=1
        elif event.startswith(('ARCOS','GAME','INPUT','LAUNCH')):
            lane=3
        else:
            lane=0
        rows.append({'ordinal':max(0,len(trace)-limit)+index+1,'event':event,
                     'label':LABELS.get(event,event.replace('_',' ').capitalize()),
                     'lane':lane,'class':record.get('class','HOST_SIM'),
                     'state':str(record.get('state','Recorded')),
                     'details':record.get('details',{})})
    return rows
