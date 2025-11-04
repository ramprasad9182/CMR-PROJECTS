from odoo import http
from odoo.http import request,Response
import logging
from bs4 import BeautifulSoup
import json
_logger = logging.getLogger(__name__)


class GETJournals(http.Controller):
    @http.route('/odoo/api/get_journal_entries_json_data', type='http', auth='public', methods=['GET'])
    def get_journal_entries_json_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Build domain based on integration flags
        if not integration.journal_entries:
            _logger.warning("No journal type selected in integration configuration.")
            return request.make_response(
                json.dumps({"message": "No journal types enabled in integration settings"}),
                headers=[('Content-Type', 'application/json')], status=400)

        domain = [('nhcl_tally_flag', '=', 'n'), ('state', '=', 'posted')]
        result = []

        # Fetch journal entries based on the provided date
        data = request.env['account.move'].sudo().search(domain)

        if not data:
            _logger.warning("No journal entries found matching the criteria.")
            return request.make_response(json.dumps({"message": "No journal entries found"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        for move in data:
            if move.narration != False:
                soup = BeautifulSoup(move.narration or '', 'html.parser')
                narration = soup.get_text()
            else:
                narration = False
            # getting payment_type
            payment_types = move.payment_ids.payment_type
            journal_entry = {
                'Odoo_id': str(move.id),
                'Date': move.date.strftime('%d-%m-%Y'),
                'Name': move.name,
                'Ref': move.ref,
                'Journal': move.journal_id.name,
                # 'Company': move.company_id.name,
                'Notes': narration,
                'Lines': []  # Prepare list for journal lines
            }

            # Add line items to the journal entry
            for line in move.line_ids:
                # siva
                name = ''
                state_name = ''
                company_name = ''
                branch = " "
                if move.move_type == 'out_invoice' and line.account_id.name == 'Debtors' and line.partner_id:
                    branch = line.partner_id.name
                elif move.move_type == 'in_invoice' and line.account_id.name == 'Creditors' and line.partner_id:
                    branch = line.partner_id.name
                elif payment_types == 'outbound' and line.account_id.name == 'Creditors':
                    branch = line.partner_id.name
                elif payment_types == 'inbound' and line.account_id.name == 'Debtors':
                    branch = line.partner_id.name

                # Convert analytic distribution to account names
                # analytic_dist = line.analytic_distribution or {}
                # print(analytic_dist)
                # analytic_distribution_named = {}
                print(line.analytic_distribution)
                for analytic_id, value in (line.analytic_distribution or {}).items():
                    analytic_ids = [int(x) for x in str(analytic_id).split(',') if x.strip()]
                    analytic_accounts = request.env['account.analytic.account'].sudo().browse(analytic_ids)

                    for analytic_account in analytic_accounts:
                        if analytic_account.exists():
                            name = analytic_account.name
                            state_name = analytic_account.acc_state_id.state_id.name if analytic_account.acc_state_id else ''
                            company_name = analytic_account.nhcl_company_name or ''
                            break  # break after first valid analytic account
                    break
                    # analytic_distribution_named = {
                        #     'CostCenter':analytic_account.name,
                        #     # 'Value': value,
                        #     'State': analytic_account.acc_state_id.state_id.name if analytic_account.acc_state_id else '',
                        #     'Company': analytic_account.company_name or ''
                        # }
                line_dict = {
                    'AccountCode': line.account_id.code,
                    'AccountName': line.account_id.name,
                    'AccountType': line.account_id.account_type,
                    'Branch': branch,  # Use "False" if no branch
                    # 'Sequence': sequence,
                    'Debit': line.debit,
                    'Credit': line.credit,
                }
                if company_name:
                    line_dict['Company'] = company_name
                if name:
                    line_dict['CostCenter'] = name
                if state_name:
                    line_dict['State'] = state_name


                # if analytic_distribution_named:
                #     line_dict['AnalyticDistribution'] = analytic_distribution_named

                journal_entry['Lines'].append(line_dict)

                # journal_entry['Lines'].append({
                #     'AccountCode': line.account_id.code,
                #     'AccountName': line.account_id.name,
                #     'AccountType': line.account_id.account_type,
                #     'Branch': branch,  # Use "False" if no branch
                #     # 'Sequence': sequence,
                #     'Debit': line.debit,
                #     'Credit': line.credit,
                #     'AnalyticDistribution': analytic_distribution_named
                # })


                # If no lines are added, log the information
            if not journal_entry['Lines']:
                _logger.warning(f"Journal entry {move.name} has no line items.")

            result.append(journal_entry)  # Append each journal entry to the result
        print(result)
        # If no valid journal entries were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid journal entries with lines found.")
            return request.make_response(json.dumps({"message":'No valid journal entries found'}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        return request.make_response(json.dumps({"Journal Entries": result}), headers=[('Content-Type', 'application/json')],status=200)

    @http.route('/odoo/api/update_flag_journal_entries_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_flag_journal_entries_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        result= []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get('Odoo_id')
            tally_id = data.get('Tally_id')
            if odoo_id:
                journal_entry = request.env['account.move'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])
                if not journal_entry:
                    existing_contact = request.env['account.move'].sudo().browse(int(odoo_id))
                    if existing_contact.exists():
                        if existing_contact.tally_record_id == tally_id:
                            if existing_contact.nhcl_tally_flag == 'y':
                                result = json.dumps({
                                    'status': 'success',
                                    'message': f'{int(odoo_id)} Id JE Record Create Flag Already Updated successfully'
                                })
                            else:
                                result = json.dumps({
                                    'status': 'info',
                                    'message': f'{int(odoo_id)} Id JE Record Create Flag value invalid'
                                })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id JE Record Tally Id Not Found'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id JE Record Not Found'
                        })
                else:
                    for je in journal_entry:
                        if request.env.company == je.company_id:
                            je.write({'nhcl_tally_flag': 'y'})
                            je.tally_record_id = tally_id
                            result = json.dumps({
                                'status': "success",
                                'message': f'{int(odoo_id)} Id Record JE Create Flag updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': "error",
                                'message': f'{int(odoo_id)} Id Record Company Mismatched'
                            })
        except Exception as e:
            result = json.dumps({
                'status': "error",
                'message': str(e)
            })

        return result

    @http.route('/odoo/api/get_updated_journal_entries_json_data', type='http', auth='public', methods=['GET'])
    def get_updated_journal_entries_json_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Build domain based on integration flags
        if not integration.journal_entries:
            _logger.warning("No journal type selected in integration configuration.")
            return request.make_response(
                json.dumps({"message": "No journal types enabled in integration settings"}),
                headers=[('Content-Type', 'application/json')], status=400)
        result = []

        # Fetch journal entries based on the provided date
        data = request.env['account.move'].sudo().search([('update_flag', '=', 'update'), ('state', '=', 'posted')])

        if not data:
            _logger.warning("No Updated journal entries found matching the criteria.")
            return request.make_response(json.dumps({"message": "No journal entries found"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        for move in data:
            if move.narration != False:
                soup = BeautifulSoup(move.narration or '', 'html.parser')
                narration = soup.get_text()
            else:
                narration = False
            journal_entry = {
                'Odoo_id': str(move.id),
                'Name': move.name,
                'Ref': move.ref,
                'Notes': narration,
            }

            result.append(journal_entry)  # Append each journal entry to the result

        # If no valid journal entries were appended, log and return a suitable response
        if not result:
            _logger.warning("No Updated Valid journal entries with lines found.")
            return request.make_response(json.dumps({'message':'No Updated Valid journal entries with lines found.'}),
                                         headers=[('Content-Type', 'application/json')],status=404)


        # Return the XML response with the appropriate content type
        return request.make_response(json.dumps({"Journal Entries": result}), headers=[('Content-Type', 'application/json')],status=200)

    @http.route('/odoo/api/update_updated_journal_entries_flag_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_journal_entries_flag_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        result = []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get('Odoo_id')
            tally_id = data.get('Tally_id')
            if odoo_id:
                # Fetch journal entries based on the provided name
                journal_entry = request.env['account.move'].sudo().search(
                    [('id', '=', int(odoo_id)), ('update_flag', '=', 'update'), ('tally_record_id', '=', tally_id)])

                if not journal_entry:
                    # Check if the contact ID exists at all
                    existing_contact = request.env['account.move'].sudo().browse(int(odoo_id))
                    if existing_contact.exists():
                        if existing_contact.tally_record_id == tally_id:
                            if existing_contact.update_flag == 'no_update':
                                result = json.dumps({
                                    'status': 'success',
                                    'message': f'{int(odoo_id)} Id JE Record Update Flag Already Updated successfully'
                                })
                            else:
                                result = json.dumps({
                                    'status': 'info',
                                    'message': f'{int(odoo_id)} Id JE Record JE Update Flag value invalid'
                                })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id JE Record Tally Id Mismatched'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id JE Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'update_flag'
                    for je in journal_entry:
                        je.write({'update_flag': 'no_update'})
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id JE Update Flag updated successfully'
                        })

        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })


        return result