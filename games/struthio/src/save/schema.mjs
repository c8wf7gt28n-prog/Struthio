// STRUTHIO ARCADE · a small JSON Schema validator for saved runs.
function typeOf(v){
if (v===null) return 'null';
if (Array.isArray(v)) return 'array';
if (typeof v==='number') return Number.isInteger(v)&&!Object.is(v,-0)?'integer':'number';
return typeof v;
}
function typeMatches(want,v){
const t=typeOf(v);
if (want==='number') return t==='number'||t==='integer';
if (want==='integer') return t==='integer';
return want===t;
}
function resolveRef(root,ref){
if (!ref.startsWith('#/')) throw new Error(`UNSUPPORTED_REF ${ref}`);
let node=root;
for (const part of ref.slice(2).split('/')) node=node[part];
if (!node) throw new Error(`BAD_REF ${ref}`);
return node;
}
function validate(schema,value,root=schema,path='$',errors=[]){
if (schema===false){errors.push(`${path}: schema false`);return errors;}
if (schema===true) return errors;
if (schema.$ref) return validate(resolveRef(root,schema.$ref),value,root,path,errors);
if (schema.type!==undefined){
const types=Array.isArray(schema.type)?schema.type:[schema.type];
if (!types.some((t)=>typeMatches(t,value))){errors.push(`${path}: expected ${types.join('|')} got ${typeOf(value)}`);return errors;}
}
if (schema.const!==undefined&&value!==schema.const) errors.push(`${path}: const ${JSON.stringify(schema.const)}`);
if (schema.enum!==undefined&&!schema.enum.some((e)=>e===value)) errors.push(`${path}: not in enum`);
if (typeof value==='number'){
if (schema.minimum!==undefined&&value<schema.minimum) errors.push(`${path}: < minimum ${schema.minimum}`);
if (schema.maximum!==undefined&&value>schema.maximum) errors.push(`${path}: > maximum ${schema.maximum}`);
}
if (typeof value==='string'&&schema.pattern!==undefined){
if (!new RegExp(schema.pattern).test(value)) errors.push(`${path}: pattern ${schema.pattern}`);
}
if (Array.isArray(value)){
if (schema.maxItems!==undefined&&value.length>schema.maxItems) errors.push(`${path}: > maxItems`);
if (schema.minItems!==undefined&&value.length<schema.minItems) errors.push(`${path}: < minItems`);
if (schema.uniqueItems){
const seen=new Set();
for (const item of value){const k=JSON.stringify(item);if (seen.has(k)){errors.push(`${path}: duplicate item`);break;}seen.add(k);}
}
const prefix=schema.prefixItems||[];
value.forEach((item,i)=>{
if (i<prefix.length) validate(prefix[i],item,root,`${path}[${i}]`,errors);
else if (schema.items!==undefined) validate(schema.items,item,root,`${path}[${i}]`,errors);
});
}
if (value!==null&&typeof value==='object'&&!Array.isArray(value)){
const props=schema.properties||{};
for (const r of schema.required||[]) if (!(r in value)) errors.push(`${path}: missing ${r}`);
for (const[k,v] of Object.entries(value)){
if (k in props) validate(props[k],v,root,`${path}.${k}`,errors);
else if (schema.additionalProperties===false) errors.push(`${path}: unknown property ${k}`);
else if (schema.additionalProperties&&typeof schema.additionalProperties==='object') validate(schema.additionalProperties,v,root,`${path}.${k}`,errors);
}
}
return errors;
}
export{validate};
