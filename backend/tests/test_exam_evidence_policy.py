import json
from pathlib import Path
import sqlite3
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_evidence import answer_state, learning_resource_completed, migrate_exam_evidence, normalize_exam


class ExamEvidencePolicyTests(unittest.TestCase):
    def test_empty_and_pending_are_not_wrong(self):
        for value in (None, '', ' ', [], {}, [' ']):
            self.assertEqual(answer_state({'user_answer': value, 'correct': False}), 'unanswered')
        self.assertEqual(answer_state({'user_answer': 0, 'correct': False}), 'incorrect')
        self.assertEqual(answer_state({'user_answer': 'A'}), 'ungraded')
        self.assertEqual(answer_state({'user_answer': 'A', 'correct': 'false'}), 'incorrect')

    def test_migration_preserves_raw_answers_and_grades(self):
        connection = sqlite3.connect(':memory:')
        connection.execute('create table exam_results(id integer,detail_json text,answers_json text,score real,total_score real)')
        detail = [{'user_answer':'A','correct':False}]*8 + [{'user_answer':'','correct':False}]*32
        connection.execute('insert into exam_results values(1,?,?,0,98)', (json.dumps(detail), '{}'))
        self.assertEqual(migrate_exam_evidence(connection), 1)
        self.assertEqual(migrate_exam_evidence(connection), 0)
        self.assertEqual(connection.execute('select incorrect_count,unanswered_count,score,total_score,profile_report_id from exam_results').fetchone(), (8,32,0,98,None))
        self.assertEqual(json.loads(connection.execute('select original_detail_json from exam_evidence_migration_audit').fetchone()[0]), detail)

    def test_prepared_resources_are_not_learning_completion(self):
        viewed = {'status':'complete','viewedAt':'now','viewSource':'learning-path-task-open'}
        self.assertFalse(learning_resource_completed('ppt', {'status':'complete'}))
        self.assertTrue(learning_resource_completed('ppt', viewed))
        self.assertFalse(learning_resource_completed('quiz', viewed))
        self.assertTrue(learning_resource_completed('quiz', {'completionSource':'exam-submission','examResultId':1,'submittedAt':'now'}))


if __name__ == '__main__': unittest.main()
