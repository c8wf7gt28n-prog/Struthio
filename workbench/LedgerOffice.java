/* Fixed UNO client. Request values are data, never Java source. */
import com.sun.star.uno.XComponentContext;
import com.sun.star.uno.UnoRuntime;
import com.sun.star.comp.helper.Bootstrap;
import com.sun.star.bridge.XUnoUrlResolver;
import com.sun.star.beans.PropertyValue;
import com.sun.star.frame.*;
import com.sun.star.lang.XComponent;
import com.sun.star.sheet.*;
import com.sun.star.table.*;
import com.sun.star.container.*;
import com.sun.star.text.*;
import com.sun.star.document.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class LedgerOffice {
 static <T>T as(Class<T> type,Object object){return UnoRuntime.queryInterface(type,object);}
 static PropertyValue property(String name,Object value){PropertyValue p=new PropertyValue();p.Name=name;p.Value=value;return p;}
 static Object load(XComponentLoader loader,String url)throws Exception{
  return loader.loadComponentFromURL(url,"_blank",0,new PropertyValue[]{property("Hidden",true),property("MacroExecutionMode",MacroExecMode.NEVER_EXECUTE),property("UpdateDocMode",UpdateDocMode.NO_UPDATE)});
 }
 static void save(Object doc,String url,String filter)throws Exception{
  as(XStorable.class,doc).storeAsURL(url,new PropertyValue[]{property("FilterName",filter),property("Overwrite",false)});
 }
 static XCellRange range(Object doc,String address)throws Exception{
  Object sheet=as(XIndexAccess.class,as(XSpreadsheetDocument.class,doc).getSheets()).getByIndex(0);
  return as(XCellRange.class,sheet).getCellRangeByName(address);
 }
 static int[] position(String address){
  int col=0,i=0;while(i<address.length() && Character.isLetter(address.charAt(i)))col=col*26+address.charAt(i++)-'A'+1;
  return new int[]{Integer.parseInt(address.substring(i))-1,col-1};
 }
 static String measured(Object doc,List<String> cells,String phase,int maxRow)throws Exception{
  XCellRange r=range(doc,"A1:C"+maxRow);
  Object[][] values=as(XCellRangeData.class,r).getDataArray();
  String[][] formulas=as(XCellRangeFormula.class,r).getFormulaArray();
  StringBuilder out=new StringBuilder();
  for(String address:cells){int[] at=position(address);Object value=values[at[0]][at[1]];
   if(!(value instanceof Number))throw new IllegalStateException("Formula produced a nonnumeric or error value: "+address);
   int error=r.getCellByPosition(at[1],at[0]).getError();
   out.append(phase+"\t"+address+"\t"+formulas[at[0]][at[1]]+"\t"+value.toString()+"\t"+error+"\n");
  }
  return out.toString();
 }
 public static void main(String[] args)throws Exception{
  XComponentContext local=Bootstrap.createInitialComponentContext(null);
  XUnoUrlResolver resolver=as(XUnoUrlResolver.class,local.getServiceManager().createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver",local));
  XComponentContext context=null;
  for(int i=0;i<100;i++){
   try{context=as(XComponentContext.class,resolver.resolve("uno:socket,host=127.0.0.1,port="+args[0]+",tcpNoDelay=1;urp;StarOffice.ComponentContext"));break;}
   catch(com.sun.star.connection.NoConnectException e){Thread.sleep(40);}
  }
  if(context==null)throw new IllegalStateException("Owned UNO endpoint unavailable");
  Object desktop=context.getServiceManager().createInstanceWithContext("com.sun.star.frame.Desktop",context);
  XComponentLoader loader=as(XComponentLoader.class,desktop);
  Object doc=load(loader,args[2]);if(doc==null)throw new IllegalStateException("Clean document not loaded");
  try{
   if(args[1].equals("CALC")){
    List<String> outputs=new ArrayList<>();List<String[]> requests=new ArrayList<>();int maxRow=1;
    for(String line:Files.readAllLines(Path.of(args[4]),StandardCharsets.UTF_8)){
     String[] f=line.split("\t",-1);maxRow=Math.max(maxRow,position(f[0])[0]+1);requests.add(f);
    }
    String[][] matrix=new String[maxRow][3];for(String[] r:matrix)Arrays.fill(r,"");
    for(String[] f:requests){String value=new String(Base64.getDecoder().decode(f[2]),StandardCharsets.UTF_8);
     if(f[1].equals("OUTPUT")){outputs.add(f[0]);continue;}
     int[] at=position(f[0]);matrix[at[0]][at[1]]=f[1].equals("formula")?"="+value:value;
    }
    as(XCellRangeFormula.class,range(doc,"A1:C"+maxRow)).setFormulaArray(matrix);
    as(XCalculatable.class,doc).calculateAll();String report=measured(doc,outputs,"CALCULATED",maxRow);
    save(doc,args[3],"calc8");as(XComponent.class,doc).dispose();doc=load(loader,args[3]);
    report+=measured(doc,outputs,"REOPENED",maxRow);Files.writeString(Path.of(args[5]),report,StandardCharsets.UTF_8);
   }else if(args[1].equals("WRITER")){
    String paragraph=Files.readString(Path.of(args[4]),StandardCharsets.UTF_8);
    XText text=as(XTextDocument.class,doc).getText();text.insertString(text.getEnd(),"\n"+paragraph,false);
    save(doc,args[3],"Office Open XML Text");as(XStorable.class,doc).storeToURL(args[6],new PropertyValue[]{property("FilterName","writer_pdf_Export")});
    as(XComponent.class,doc).dispose();doc=load(loader,args[3]);
    Files.writeString(Path.of(args[5]),as(XTextDocument.class,doc).getText().getString(),StandardCharsets.UTF_8);
   }else throw new IllegalArgumentException("Unsupported fixed Office profile");
  }finally{as(XComponent.class,doc).dispose();as(XDesktop.class,desktop).terminate();}
  System.exit(0);
 }
}
