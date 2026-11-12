"""Finite acyclic support/refutation paths, scoped to declared proposed rules.

This is a dependency calculator. It cannot establish the truth of a model's
interpretation, missing dependencies, a physical design or an assumption.
"""
from itertools import product
from math import prod
import re
from .project_desk import digest

NAME=re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,39}$')


def validate(graph):
    if type(graph) is not dict or set(graph)!={'nodes','rules','target','assumptions','coverage'}:raise ValueError('REASON_GRAPH_FIELDS')
    if graph['coverage'] not in ('DECLARED_FINITE_GRAPH','UNKNOWN'):raise ValueError('REASON_COVERAGE')
    if not isinstance(graph['assumptions'],list) or not 1<=len(graph['assumptions'])<=32 or any(type(x) is not str or not x or len(x)>1000 for x in graph['assumptions']):raise ValueError('REASON_ASSUMPTION_CONTEXT_REQUIRED')
    if not isinstance(graph['nodes'],list) or not 1<=len(graph['nodes'])<=64 or not isinstance(graph['rules'],list) or len(graph['rules'])>128:raise ValueError('REASON_GRAPH_BUDGET')
    nodes={};rules={}
    for node in graph['nodes']:
        if type(node) is not dict or not NAME.fullmatch(str(node.get('id',''))) or node['id'] in nodes:raise ValueError('REASON_NODE_ID')
        base={'id','kind','label'}
        if type(node.get('label')) is not str or not 1<=len(node['label'])<=500:raise ValueError('REASON_NODE_LABEL')
        if node['kind']=='ATOM':
            if node.get('source') not in ('MATH','EXPERIMENT','BOARD') or not re.fullmatch('[0-9a-f]{32}',str(node.get('receipt',''))):raise ValueError('REASON_RECEIPT_REFERENCE')
            if type(node.get('expected')) is not bool:raise ValueError('REASON_BOOLEAN_PREDICATE_ONLY')
            allowed=base|{'source','receipt','expected'}|({'index'} if node['source']=='MATH' else {'measurement'} if node['source']=='EXPERIMENT' else set())
            if node['source']=='MATH' and (type(node.get('index')) is not int or not 0<=node['index']<64):raise ValueError('REASON_OUTPUT_INDEX')
            if node['source']=='EXPERIMENT' and (type(node.get('measurement')) is not str or not node['measurement']):raise ValueError('REASON_MEASUREMENT')
        elif node['kind']=='ASSUMPTION':
            allowed=base
            if node['label'] not in graph['assumptions']:raise ValueError('REASON_UNDECLARED_ASSUMPTION')
        elif node['kind']=='CLAIM':allowed=base
        else:raise ValueError('REASON_NODE_KIND')
        if set(node)!=allowed:raise ValueError('REASON_NODE_FIELDS')
        nodes[node['id']]=node
    if graph['target'] not in nodes or nodes[graph['target']]['kind']!='CLAIM':raise ValueError('REASON_TARGET')
    edges={name:set() for name in nodes}
    for rule in graph['rules']:
        if type(rule) is not dict or set(rule)!={'id','conclusion','polarity','premises'} or not NAME.fullmatch(str(rule['id'])) or rule['id'] in rules:raise ValueError('REASON_RULE_FIELDS')
        if rule['conclusion'] not in nodes or nodes[rule['conclusion']]['kind']!='CLAIM' or rule['polarity'] not in ('positive','negative'):raise ValueError('REASON_RULE_CONCLUSION')
        if not isinstance(rule['premises'],list) or not 1<=len(rule['premises'])<=8:raise ValueError('REASON_RULE_PREMISES')
        seen=set()
        for premise in rule['premises']:
            if type(premise) is not dict or set(premise)!={'id','polarity'} or premise['id'] not in nodes or premise['polarity'] not in ('positive','negative'):raise ValueError('REASON_UNKNOWN_PREMISE')
            pair=(premise['id'],premise['polarity'])
            if pair in seen:raise ValueError('REASON_DUPLICATE_PREMISE')
            seen.add(pair);edges[rule['conclusion']].add(premise['id'])
        rules[rule['id']]=rule
    visited=set();active=set();order=[]
    def visit(name):
        if name in active:raise ValueError('REASON_UNSUPPORTED_CYCLE')
        if name in visited:return
        active.add(name)
        for parent in sorted(edges[name]):visit(parent)
        active.remove(name);visited.add(name);order.append(name)
    for name in nodes:visit(name)
    return nodes,rules,order,edges


def compute(graph, observations):
    from .stac.evidence import EvidenceSupport
    nodes,rules,order,edges=validate(graph);values={};paths={};inactive=[]
    for name in order:
        node=nodes[name];positive=[];negative=[]
        if node['kind']=='ASSUMPTION':positive=[{'atoms':[],'assumptions':[name],'rules':[]}]
        elif node['kind']=='ATOM':
            obs=observations[name]
            if obs['applicability']=='CURRENT' and obs['state']=='OBSERVED':
                path={'atoms':[name],'assumptions':[],'rules':[]}
                (positive if obs['value']==node['expected'] else negative).append(path)
            else:inactive.append({'id':name,'reason':obs['state'],'applicability':obs['applicability']})
        else:
            for rule in rules.values():
                if rule['conclusion']!=name:continue
                alternatives=[paths[p['id']][p['polarity']] for p in rule['premises']]
                if prod(len(paths) for paths in alternatives)>4096:raise ValueError('REASON_COMBINATION_BUDGET')
                for combination in product(*alternatives):
                    path={key:sorted(set(x for part in combination for x in part[key])) for key in ('atoms','assumptions','rules')}
                    path['rules']=sorted(set(path['rules']+[rule['id']]))
                    target=positive if rule['polarity']=='positive' else negative
                    if path not in target:target.append(path)
                    if len(positive)+len(negative)>256:raise ValueError('REASON_PATH_BUDGET: simplify the finite graph')
        positive.sort(key=digest);negative.sort(key=digest)
        paths[name]={'positive':positive,'negative':negative}
        values[name]=EvidenceSupport(bool(positive),bool(negative)).state.value
    target=graph['target']
    closure=set()
    def reach(name):
        if name in closure:return
        closure.add(name)
        for parent in edges[name]:reach(parent)
    reach(target)
    return {'state':values[target],'states':values,'target':target,'paths':paths[target],'all_paths':paths,
        'reason_digest':digest(paths[target]),'inactive_atoms':inactive,'observations':observations,
        'coverage':{'declared':graph['coverage'],'tracked_target_dependencies':sorted(closure),
                    'outside_graph':'UNKNOWN','missing_dependency_excludes_no_impact_claim':True},
        'applicability':'CURRENT_WITHIN_DECLARED_GRAPH','rule_review':'PROPOSED_RULES_NOT_APPROVED_FACTS',
        'assumption_context':graph['assumptions'],'physical_qualification':False,'model_invoked':False}
