"""Bounded engineering case methods; source identity is not board acceptance.

The simulation recipe and exact oracle are frozen before an evaluation input
is chosen. Expected answers for held-out evaluations live outside this module.
"""
from __future__ import annotations
import hashlib,re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from . import record_store as records,evidence_contracts as evidence

VERSION='arc.engineering-case/1'
ROOT='hardware/compact-arc1/R10_WORK/'
CORE=ROOT+'fpga12/rtl/psram_qspi_core.sv'
MODEL=ROOT+'fpga12/sim/aps6404l_model_r07.sv'
TOP=ROOT+'fpga12/rtl/r10_support_mem_top.sv'
BENCH=ROOT+'fpga12/tb/tb_r10_support_mem.sv'
LOADER=ROOT+'firmware/d213_flashless_proof/loader/r10_d213_start.c'
HEADER=ROOT+'firmware/d213_flashless_proof/loader/r10_d213_start.h'
DOC='docs/vendor/datasheets/aps3204l.pdf'
def digest(value):return hashlib.sha256(records.canonical(value)).hexdigest()
def fingerprint():return hashlib.sha256(Path(__file__).read_bytes()+Path(evidence.__file__).read_bytes()).hexdigest()
def clean(text):return re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)
def safe_hdl(text):
    if len(text.encode())>1024*1024:raise ValueError('CASE_HDL_INPUT_BUDGET')
    text=clean(text);tasks=set(re.findall(r'\$([A-Za-z_]\w*)',text));directives=set(re.findall(r'`([A-Za-z_]\w*)',text))
    if tasks-{'clog2','display','finish','fatal','time','realtime','random'} or directives-{'timescale','default_nettype','ifdef','ifndef','else','endif'} or re.search(r'\b(?:import|export)\s+"DPI',text):raise ValueError('CASE_HDL_FOREIGN_OR_FILE_IO_REQUIRES_REVIEW')
def parameters(text):
    """Literal named parameters on the one declared wrapper instance only."""
    text=clean(text)
    matches=list(re.finditer(r'\bpsram_user_port\s*#\s*\((.*?)\)\s*u_psram\s*\(',text,re.S))
    if len(matches)!=1:raise ValueError('CASE_PSRAM_WRAPPER_BINDING_UNRESOLVED')
    body=matches[0][1];out={}
    for name in ('MCLK_HZ','CLK_DIV','BUF_BYTES','TCEM_NS'):
        values=re.findall(r'\.'+name+r'\s*\(\s*([0-9]+)\s*\)',body)
        if len(values)!=1:raise ValueError('CASE_NONLITERAL_OR_DUPLICATE_PARAMETER')
        out[name]=int(values[0])
    return out
def source_lines(path,raw,first,last):
    lines=raw.decode('utf-8-sig').splitlines()
    if not 1<=first<=last<=len(lines) or last-first>=80:raise ValueError('CASE_SOURCE_LINE_BOUND')
    text='\n'.join(lines[first-1:last])
    if len(text.encode())>12000:raise ValueError('CASE_SOURCE_EXCERPT_BUDGET')
    return {'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'locator':{'kind':'source_lines','line_start':first,'line_end':last},'text':text}
def locate(path,raw,needle,before=2,after=3):
    lines=raw.decode('utf-8-sig').splitlines();hits=[i for i,line in enumerate(lines,1) if needle in line]
    if not hits:raise ValueError('CASE_SOURCE_ANCHOR_UNAVAILABLE')
    return source_lines(path,raw,max(1,hits[0]-before),min(len(lines),hits[0]+after))
def vendor_limits(pages,mpn):
    by={p['page_index']:p for p in pages}
    if len(pages)!=4 or set(by)!={0,5,25,26} or mpn!='APS3204L-3SQNA-SN':raise ValueError('CASE_VENDOR_PROFILE_NOT_APPLICABLE')
    first=by[0]['text'];order=by[5]['text'];timing=by[25]['text'];changes=by[26]['text']
    if not all(mpn in p['text'] for p in pages) or not re.search(r'3\s*[µμu]s\s+Extended grade',timing) or not re.search(r'8\s*[µμu]s\s+Standard grade',timing) or 'Table 9' not in timing or not re.search(r'-40\s*°?C\s+to\s+\+105\s*°?C',order) or not re.search(r'3us\s*@105C',changes):raise ValueError('CASE_VENDOR_GRADE_TABLE_REVIEW_REQUIRED')
    return {'parameter':'tCEM','extended':evidence.quantity('3','us'),'standard':evidence.quantity('8','us'),
      'case_grade':'EXTENDED_105_C','conditions':'Nominal APS3204L-3SQNA-SN; vendor Tc range -40 to +105 C; 3 us at 105 C in change log. Physical fitment and operating point unverified.',
      'source_pages':[{'record_id':p['record_id'],'sha256':p['source_sha256'],'page_index':p['page_index'],'page_label':p['page_label']} for p in pages],
      'review':'SOURCE_INTERPRETATION_PENDING_INDEPENDENT_REVIEW','fitted_grade_accepted':False}
def pulse_oracle(text,limit_ns):
    """Independent of the model's verdict: measure recorded CE# pulse widths."""
    if not isinstance(text,str) or len(text.encode())>2*1024*1024 or limit_ns not in (3000,8000):raise ValueError('CASE_TRACE_BOUND')
    widths=[]
    for token in re.findall(r'^CASE_CE_NS ([0-9]+(?:\.[0-9]{1,3})?)$',text,re.M):widths.append(Fraction(Decimal(token)))
    if not widths or len(widths)>256:raise ValueError('CASE_TRACE_PULSES_MISSING_OR_LIMIT')
    summary=re.findall(r'^CASE_RESULT violations=(\d+) bytes=(\d+)$',text,re.M)
    if len(summary)!=1:raise ValueError('CASE_TRACE_RESULT_MISSING_OR_DUPLICATE')
    violations=int(summary[0][0]);maximum=max(widths);bad=sum(v>limit_ns for v in widths)
    return {'state':'FAIL' if bad or violations else 'PASS','limit':evidence.quantity(str(limit_ns),'ns'),
      'pulse_count':len(widths),'max_ce_low_ns':str(Decimal(maximum.numerator)/Decimal(maximum.denominator)),
      'ce_limit_violations':bad,'model_violations':violations,'written_bytes':int(summary[0][1]),'scope':'HOST_RTL_CASE_WITH_BEHAVIORAL_STAND_IN_NOT_PHYSICAL_QUALIFICATION'}
def usb_classification(endpoints,source_texts,assumed_direct_controller):
    members=sorted({(p['reference'],p['pin']) for p in endpoints});code='\n'.join(clean(s) for s in source_texts)
    callbacks=all(re.search(r'->'+n+r'\s*\(',code) for n in ('request_internal_mux','observe_internal_mux','observe_no_service_host'))
    adapter=bool(re.search(r'\.request_internal_mux\s*=',code))
    return {'state':'UNRESOLVED','direct_control_assumption':'SUPPORTED_NATIVE_MEMBERSHIP_ONLY' if any(r==assumed_direct_controller for r,p in members) else 'CONFLICTS_WITH_DIRECT_NATIVE_NET_MEMBERSHIP',
      'assumption':{'kind':'QUESTION_NOT_ACCEPTED_SOURCE_FACT','direct_controller':assumed_direct_controller},'native_endpoints':[{'reference':r,'pin':p} for r,p in members],
      'loader_requests_and_observes_mux':callbacks,'adapter_initializer_found_in_reviewed_source_set':adapter,
      'conclusion':'Loader callback sequencing cannot identify the physical mux driver or prove external-host isolation. Bind the board adapter and qualify its observations.',
      'physical_qualification':False,'automatic_fix':'NONE'}
def variation(value):
    if not isinstance(value,dict) or set(value)!={'clock_hz','length','address'}:raise ValueError('CASE_VARIATION_FIELDS')
    if any(type(v) is not int for v in value.values()) or not 40000000<=value['clock_hz']<=50000000 or value['clock_hz']%1000000 or not 64<=value['length']<=256 or not 0<=value['address']<=4096:raise ValueError('CASE_VARIATION_BOUNDS')
    return value

def testbench(controller_ns,oracle_ns,v):
    variation(v)
    if controller_ns not in (3000,8000) or oracle_ns not in (3000,8000):raise ValueError('CASE_TIMING_PROFILE_BOUND')
    return '''`timescale 1ns/1ps
module ledger_psram_case;
reg clk=0,rst=1,cmd_valid=0; wire cmd_ready,done_valid,ready,error;
wire [2:0] done_status; wire [1:0] err_code; wire [7:0] id_mfid,id_kgd;
wire [7:0] wbuf_raddr,rbuf_waddr,rbuf_wdata; reg [7:0] wbuf_rdata=0; wire rbuf_we;
wire psram_ce_n,psram_sclk; wire [3:0] psram_dq_o,psram_dq_oe; wire [3:0] sio;
reg [7:0] data [0:255]; integer i; realtime started;
always #('''+str(10**9/(2*v['clock_hz']))+''') clk=~clk;
always @(posedge clk) wbuf_rdata<=data[wbuf_raddr];
genvar bitnum; generate for(bitnum=0;bitnum<4;bitnum=bitnum+1) begin
assign sio[bitnum]=psram_dq_oe[bitnum]?psram_dq_o[bitnum]:1'bz; end endgenerate
psram_qspi_core #(.MCLK_HZ('''+str(v['clock_hz'])+'''),.CLK_DIV(1),.BUF_BYTES(256),.TCEM_NS('''+str(controller_ns)+''')) dut(
.clk(clk),.rst(rst),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_write(1'b1),.cmd_addr(23'd'''+str(v['address'])+'''),.cmd_len(9'd'''+str(v['length'])+'''),
.done_valid(done_valid),.done_status(done_status),.init_req(1'b0),.wbuf_raddr(wbuf_raddr),.wbuf_rdata(wbuf_rdata),
.rbuf_we(rbuf_we),.rbuf_waddr(rbuf_waddr),.rbuf_wdata(rbuf_wdata),.ready(ready),.error(error),.err_code(err_code),.id_mfid(id_mfid),.id_kgd(id_kgd),
.dbg_freeze(1'b0),.psram_ce_n(psram_ce_n),.psram_sclk(psram_sclk),.psram_dq_o(psram_dq_o),.psram_dq_oe(psram_dq_oe),.psram_dq_i(sio));
aps6404l_model_r07 #(.TCEM_NS('''+str(oracle_ns)+'''.0)) model(.ce_n(psram_ce_n),.sclk(psram_sclk),.sio(sio));
always @(negedge psram_ce_n) started=$realtime;
always @(posedge psram_ce_n) if(started>0) $display("CASE_CE_NS %0.3f",$realtime-started);
initial begin
for(i=0;i<256;i=i+1) data[i]=i^165;
repeat(5) @(negedge clk); rst=0;
wait(ready||error); if(error) $fatal(1,"CASE_INIT_FAILURE");
@(negedge clk); cmd_valid=1; @(negedge clk); cmd_valid=0;
wait(done_valid); if(done_status!=0||error) $fatal(1,"CASE_COMMAND_FAILURE");
#100; $display("CASE_RESULT violations=%0d bytes=%0d",model.violations,model.n_bytes_w);
if(model.violations!=0) $fatal(1,"CASE_ORACLE_FAIL");
$display("CASE_ORACLE_PASS"); $finish;
end
initial begin #1000000; $fatal(1,"CASE_TIMEOUT"); end
endmodule
'''
