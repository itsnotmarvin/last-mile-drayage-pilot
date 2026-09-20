"""Application workflow over shared Neo4j evidence and private confirmed cases."""
from neo4j_kg.assessment import TripService
from .extraction import suggest
from .store import Conflict
from neo4j_kg.trip_state import TripNotFound


class Application:
    def __init__(self, workspace, graph):
        self.workspace = workspace
        self.assessments = TripService(graph, workspace.trips)

    def capture(self, token, csrf, cid, version, statement, request_key):
        mid = self.workspace.message(token, csrf, cid, version, statement, request_key)
        current = self.workspace.view(token, cid)
        # A retry of an old statement cannot repropose it after a newer message.
        if current['conversation']['version'] == version + 1 and current['messages'][-1]['id'] == mid:
            if not current['proposals']:
                self.workspace.propose_local(token, csrf, cid, mid, version + 1, suggest(statement))
        return self.view(token, cid)

    def confirm(self, token, csrf, cid, proposal_id, version, facts, scope):
        self.workspace.confirm(token, csrf, cid, proposal_id, version, facts, scope)
        return self.view(token, cid)

    def view(self, token, cid):
        result = self.workspace.view(token, cid)
        result['assessment'] = None
        result['assessment_state'] = 'review_required' if result['messages'] else 'statement_required'
        if result['ready_for_assessment']:
            assessment = self.assessments.assess({'trip_id': result['case']['trip_id']})
            # Neo4j reads occur outside SQLite locks. Do not send findings whose
            # statement, confirmed case, identity, or access changed during the read.
            self.workspace.assert_current(token, cid, result['conversation']['version'])
            if assessment['case']['revision'] != result['case']['revision']:
                raise Conflict('The trip changed during assessment. Reload.')
            result['assessed_at'] = self.workspace.clock()
            result['assessment'] = assessment
            result['assessment_state'] = assessment['service_status']
        return result

    def model_assessment(self, capability, message_id, version):
        before = self.workspace.model_assessment_context(capability, message_id, version)
        try:
            assessment = self.assessments.assess({'trip_id': before['case']['trip_id']})
        except TripNotFound:
            raise Conflict('Confirmed trip changed during assessment') from None
        # Reauthorize after graph I/O: revocation, expiry, sharing, new messages,
        # confirmations and out-of-band case revisions must suppress this response.
        after = self.workspace.model_assessment_context(capability, message_id, version)
        if before != after or assessment['case']['revision'] != after['case']['revision']:
            raise Conflict('Confirmed trip changed during assessment')
        from neo4j_kg.answer_guidance import explanation_package
        return {'schema_version':'drayage-confirmed-explanation-v1',
                'binding': {'conversation_id':after['conversation_id'], 'conversation_version':version,
                            'message_id':message_id, 'trip_id':after['case']['trip_id'],
                            'trip_revision':after['case']['revision'], 'assessment_id':assessment['assessment_id']},
                'assessed_at':self.workspace.clock(), 'confirmation':after['confirmation'],
                'original_statements':after['statements'], 'reported_facts':assessment['case']['facts'],
                'explanation':explanation_package(assessment),
                'validity':'Snapshot only. Fetch again before each new answer; a new statement requires application review and confirmation.'}
