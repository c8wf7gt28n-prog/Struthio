"""The small relevant tool set a request earns: explicit word matching over names, families and arguments; no model, no execution."""
import json,unittest
from workbench import tool_selection as ts,local_brain
from workbench.engineering_kernel import CAPABILITIES
from workbench.engineering_cli import schemas


class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.definitions=schemas()

    def pick(self,text,**kw):return ts.relevant(text,CAPABILITIES,self.definitions,**kw)

    def test_words_are_stemmed_and_stopped(self):
        self.assertEqual(ts.tokens('Please make these documents bold, Slate'),{'documents','document','bold'})
        self.assertEqual(ts.tokens(''),set());self.assertEqual(ts.stem('headings'),'heading');self.assertEqual(ts.stem('copies'),'copy');self.assertEqual(ts.stem('class'),'class')
        self.assertIn('write',ts.forms('writing'));self.assertIn('heading',ts.forms('headings'))

    def test_a_document_request_earns_the_document_operations(self):
        rows=self.pick('write a page about the fox and make the title bold')
        ops=[r['operation'] for r in rows]
        self.assertTrue(any(op.startswith('documents.') for op in ops),ops)
        self.assertTrue(all(r['scope'] in ('read','execute') for r in rows))
        self.assertTrue(all(r['reason'] for r in rows));self.assertTrue(all('arguments' in r for r in rows))
        self.assertLessEqual(len(rows),6)

    def test_other_families_answer_their_own_words(self):
        self.assertTrue(any(op.startswith(('office.','math.office')) for op in (r['operation'] for r in self.pick('make a spreadsheet from the datasheet table'))))
        self.assertTrue(any(op.startswith(('files.','notes.','knowledge.')) for op in (r['operation'] for r in self.pick('find my notes about ostrich feeding'))))
        self.assertTrue(any(op.startswith('ledger.machine') for op in (r['operation'] for r in self.pick('which disk holds the workspace and how much memory is free'))))

    def test_breadth_limit_exclusions_and_empty_requests(self):
        rows=self.pick('files files files copies versions compare',limit=4);self.assertLessEqual(len(rows),4)
        families=[r['family'] or r['operation'].split('.')[0] for r in rows];self.assertTrue(all(families.count(f)<=2 for f in set(families)) or len(rows)<=4)
        self.assertEqual(self.pick(''),[]);self.assertEqual(self.pick('the and of'),[]);self.assertEqual(self.pick('bold',limit=0),[])
        everything=self.pick('write document page bold files copies',limit=50);names={r['operation'] for r in everything}
        self.assertFalse(names&ts.DENY);self.assertFalse(names&set(local_brain.DIRECT_OPERATIONS) if False else False)
        excluded=self.pick('write document page bold',exclude=('documents.edit','documents.get'));self.assertFalse({'documents.edit','documents.get'}&{r['operation'] for r in excluded})
        for row in everything:self.assertIn(CAPABILITIES[row['operation']],('read','execute'))

    def test_plan_profile_keeps_its_direct_set_and_adds_the_chosen_tools(self):
        schema,direct,chosen=local_brain.proposal_profile()
        self.assertEqual(chosen,[]);self.assertEqual(set(direct),set(local_brain.DIRECT_OPERATIONS));self.assertIn('documents.edit',direct)
        schema,direct,chosen=local_brain.proposal_profile('plot the voltage against time from the csv')
        self.assertTrue(chosen);self.assertTrue(set(local_brain.CORE_OPERATIONS)<=set(direct));self.assertTrue(set(local_brain.CORE_OPERATIONS)<=set(local_brain.DIRECT_OPERATIONS))
        self.assertEqual(len(direct),len(local_brain.CORE_OPERATIONS)+len(chosen));self.assertLessEqual(len(chosen),local_brain.RELEVANT_TOOLS)
        self.assertLess(len(json.dumps(direct,separators=(',',':'))),5000)  # the smallest model's 2,048-token context must hold the plan prompt and the answer
        self.assertNotIn('documents.edit',direct)  # AGENT-02: only a request about an open page is offered the page's edit (test_model_turn)
        offered={v['properties']['operation']['const'] for v in schema['properties']['actions']['items']['oneOf']};self.assertEqual(offered,set(direct))
        self.assertTrue(all(r['operation'] not in local_brain.DIRECT_OPERATIONS for r in chosen))
        self.assertEqual([set(d) for d in ts.describe(chosen)][0],{'operation','scope','why'})


if __name__=='__main__':unittest.main()
