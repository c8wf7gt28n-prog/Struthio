/* Fixed owned Calc session. Commands are data; no macros or source execution. */
import com.sun.star.uno.UnoRuntime;
import com.sun.star.uno.XComponentContext;
import com.sun.star.comp.helper.Bootstrap;
import com.sun.star.bridge.XUnoUrlResolver;
import com.sun.star.beans.PropertyValue;
import com.sun.star.frame.*;
import com.sun.star.lang.XComponent;
import com.sun.star.lang.SystemDependent;
import com.sun.star.awt.*;
import com.sun.star.sheet.*;
import com.sun.star.table.*;
import com.sun.star.container.*;
import com.sun.star.document.*;
import com.sun.star.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class LedgerSession {
 static <T>T as(Class<T> type,Object object){return UnoRuntime.queryInterface(type,object);}
 static PropertyValue property(String name,Object value){PropertyValue p=new PropertyValue();p.Name=name;p.Value=value;return p;}
 static String enc(String value){return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));}
 static void atomic(Path path,String value)throws Exception{
  Path tmp=path.resolveSibling(path.getFileName()+".tmp");Files.writeString(tmp,value,StandardCharsets.UTF_8);
  Files.move(tmp,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
 }
 static XCell cell(Object sheet,String address)throws Exception{return as(XCellRange.class,sheet).getCellRangeByName(address).getCellByPosition(0,0);}
 static void protect(Object sheet,Object doc,boolean locked)throws Exception{
  XModifiable modified=as(XModifiable.class,doc);boolean before=modified.isModified();
  XProtectable protection=as(XProtectable.class,sheet);
  if(protection==null)throw new IllegalStateException("Owned sheet protection unavailable");
  if(locked&&!protection.isProtected())protection.protect("");
  if(!locked&&protection.isProtected())protection.unprotect("");
  modified.setModified(before);
 }
 static void save(Object doc)throws Exception{
  if(as(XModifiable.class,doc).isModified())as(XStorable.class,doc).store();
 }
 static String inspect(Object doc,Object sheet,List<String[]> cells,String id,String mode,String title,long handle)throws Exception{
  XWindow2 window=as(XWindow2.class,as(XModel.class,doc).getCurrentController().getFrame().getContainerWindow());
  StringBuilder out=new StringBuilder("SESSION\t"+id+"\t"+mode+"\t"+(window!=null&&window.isVisible())+"\t"+handle+"\t"+enc(title)+"\n");
  for(String[] row:cells){XCell c=cell(sheet,row[0]);String unit=as(com.sun.star.text.XTextRange.class,cell(sheet,"C"+row[0].substring(1))).getString();
   out.append("CELL\t"+row[0]+"\t"+enc(c.getFormula())+"\t"+Double.toString(c.getValue())+"\t"+c.getType().getValue()+"\t"+enc(unit)+"\t"+c.getError()+"\n");
  }
  return out.toString();
 }
 public static void main(String[] args){
  try{run(args);}catch(Throwable failure){failure.printStackTrace();System.exit(1);}
 }
 static void run(String[] args)throws Exception{
  if(args.length==1&&args[0].equals("--check-source")){System.out.println("LedgerSession source compiled; native window not tested.");return;}
  XComponentContext local=Bootstrap.createInitialComponentContext(null);
  XUnoUrlResolver resolver=as(XUnoUrlResolver.class,local.getServiceManager().createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver",local));
  XComponentContext context=null;
  for(int i=0;i<200;i++){try{context=as(XComponentContext.class,resolver.resolve("uno:socket,host=127.0.0.1,port="+args[0]+",tcpNoDelay=1;urp;StarOffice.ComponentContext"));break;}catch(com.sun.star.connection.NoConnectException e){Thread.sleep(40);}}
  if(context==null)throw new IllegalStateException("Owned endpoint unavailable");
  Object desktop=context.getServiceManager().createInstanceWithContext("com.sun.star.frame.Desktop",context);
  Object doc=as(XComponentLoader.class,desktop).loadComponentFromURL(args[1],"_blank",0,new PropertyValue[]{property("Hidden",false),property("MacroExecutionMode",MacroExecMode.NEVER_EXECUTE),property("UpdateDocMode",UpdateDocMode.NO_UPDATE)});
  if(doc==null)throw new IllegalStateException("Owned working document unavailable");
  Object sheet=as(XIndexAccess.class,as(XSpreadsheetDocument.class,doc).getSheets()).getByIndex(0);
  List<String[]> cells=new ArrayList<>();Set<String> inputs=new HashSet<>();
  for(String line:Files.readAllLines(Path.of(args[2]),StandardCharsets.UTF_8)){
   String[] row=line.split("\t",-1);if(!row[0].matches("B[1-9][0-9]{0,3}"))throw new IllegalArgumentException("Cell outside fixed profile");
   cells.add(row);if(row[1].equals("INPUT"))inputs.add(row[0]);
  }
  XFrame frame=as(XModel.class,doc).getCurrentController().getFrame();XWindow window=frame.getContainerWindow();
  window.setPosSize(15,15,1280,880,(short)15);window.setVisible(true);
  String title="Ledger working calculation "+args[5];XTitle xtitle=as(XTitle.class,frame);if(xtitle!=null)xtitle.setTitle(title);
  XSystemDependentWindowPeer peer=as(XSystemDependentWindowPeer.class,window);long handle=0;
  if(peer!=null){Object h=peer.getWindowHandle(new byte[0],SystemDependent.SYSTEM_XWINDOW);
   if(h instanceof com.sun.star.uno.Any)h=((com.sun.star.uno.Any)h).getObject();
   if(h instanceof SystemDependentXWindow)handle=Integer.toUnsignedLong(((SystemDependentXWindow)h).WindowHandle);
   else if(h instanceof Number)handle=((Number)h).longValue();
  }
  XWindow2 visible=as(XWindow2.class,window);
  if(visible==null||!visible.isVisible()||handle==0)throw new IllegalStateException("A real visible X11 Calc window is required; headless is not visible qualification");
  Path folder=Path.of(args[3]);String mode="PAUSED";protect(sheet,doc,true);
  atomic(folder.resolve("ready.tsv"),inspect(doc,sheet,cells,"READY",mode,title,handle));
  long deadline=System.nanoTime()+Long.parseLong(args[4])*1000000000L;
  try{
   while(System.nanoTime()<deadline){
    Path command=folder.resolve("command.tsv");
    if(Files.exists(command)){
     String[] f=Files.readString(command).strip().split("\t",-1);Files.delete(command);
     String id=f[0],op=f[1];boolean close=false;
     try{
      switch(op){
       case "TAKEOVER":mode="TAKEOVER";protect(sheet,doc,false);break;
       case "PAUSE":save(doc);mode="PAUSED";protect(sheet,doc,true);break;
       case "RESUME":save(doc);mode="AUTOMATION";protect(sheet,doc,true);break;
       case "EDIT":
        if(!mode.equals("TAKEOVER")||f.length!=4||!inputs.contains(f[2]))throw new IllegalArgumentException("Edit requires owner takeover and a declared input cell");
        double value=Double.parseDouble(new String(Base64.getDecoder().decode(f[3]),StandardCharsets.UTF_8));
        if(!Double.isFinite(value))throw new IllegalArgumentException("Nonfinite input");
        cell(sheet,f[2]).setValue(value);as(XCalculatable.class,doc).calculateAll();save(doc);break;
       case "RECALCULATE":
        if(!mode.equals("AUTOMATION"))throw new IllegalStateException("Session is paused for owner control");
        boolean modified=as(XModifiable.class,doc).isModified();as(XCalculatable.class,doc).calculateAll();as(XModifiable.class,doc).setModified(modified);break;
       case "SAVE_INSPECT":save(doc);break;
       case "INSPECT":break;
       case "CLOSE":save(doc);close=true;mode="CLOSED";break;
       default:throw new IllegalArgumentException("Unsupported session command");
      }
      atomic(folder.resolve("reply-"+id+".tsv"),inspect(doc,sheet,cells,id,mode,title,handle));
      if(close)break;
     }catch(Exception e){atomic(folder.resolve("reply-"+id+".tsv"),"ERROR\t"+id+"\t"+enc(e.getClass().getSimpleName()+": "+e.getMessage())+"\n");}
    }
    if(mode.equals("TAKEOVER"))save(doc);
    Thread.sleep(200);
   }
  }finally{
   save(doc);as(XComponent.class,doc).dispose();as(XDesktop.class,desktop).terminate();
  }
  System.exit(0);
 }
}
