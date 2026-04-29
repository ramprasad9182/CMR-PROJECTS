from odoo import http
from odoo.http import request,Response
import logging
from bs4 import BeautifulSoup
import json
_logger = logging.getLogger(__name__)


class GETJournals(http.Controller):
    def _validation_response(self, kwargs):
        """Validate integration and API key. Return (integration, error_response_or_None)."""
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)
        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return None, request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                               headers=[('Content-Type', 'application/json')], status=404)
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return None, request.make_response(json.dumps({"message": "Invalid API key"}),
                                               headers=[('Content-Type', 'application/json')], status=404)
        return integration, None

    def _serialize_move_with_lines(self, move):
        """Return (payload_dict, skip_bool) using same ‘Lines’ logic as your JE API."""
        # Notes / narration (plain text)
        if move.narration is not False:
            soup = BeautifulSoup(move.narration or '', 'html.parser')
            narration = soup.get_text()
        else:
            narration = False

        journal_entry = {
            'Odoo_id': str(move.id),
            'Date': move.date.strftime('%d-%m-%Y'),
            'Name': move.name,
            'Ref': move.ref,
            'Journal': move.journal_id.name,
            'Notes': narration,
            'Lines': []
        }

        branch = " "
        # For each line, compute CostCenter/State/Company from analytic_distribution
        # If any line lacks required CostCenter/Company -> skip entire entry, as per your logic.
        for line in move.line_ids:
            cos_name = ''
            state_name = ''
            company_name = ''

            # analytic_distribution can contain multiple keys; keep your original approach
            for analytic_id, value in (line.analytic_distribution or {}).items():
                analytic_ids = [int(x) for x in str(analytic_id).split(',') if x.strip()]
                analytic_accounts = request.env['account.analytic.account'].sudo().browse(analytic_ids)
                for aa in analytic_accounts:
                    if aa.exists():
                        cos_name = aa.name or ''
                        state_name = aa.acc_state_id.state_id.name if aa.acc_state_id else ''
                        company_name = aa.nhcl_company_name or ''
                        break
                break  # only first key used (same as your code)

            if not cos_name or not company_name:
                _logger.info(f"Skipping move {move.name} due to missing CostCenter/Company in line {line.id}")
                return None, True  # skip

            # derive Branch from any payable line's partner
            if line.account_id.account_type == 'liability_payable':
                branch = line.partner_id.name
            elif line.account_id.account_type == 'asset_receivable':
                branch = line.partner_id.name
            else:
                branch = " "

            line_dict = {
                'AccountCode': line.account_id.code,
                'AccountName': line.account_id.name,
                'AccountType': line.account_id.account_type,
                'Branch': branch if branch else False,
                'Debit': line.debit,
                'Credit': line.credit,
            }
            if company_name:
                line_dict['Company'] = company_name
            if cos_name:
                line_dict['CostCenter'] = cos_name
            if state_name:
                line_dict['State'] = state_name

            journal_entry['Lines'].append(line_dict)

        if not journal_entry['Lines']:
            _logger.warning(f"Move {move.name} has no line items.")
        return journal_entry, False

    def _invoice_serialize_move_with_lines(self, move):
        """Return (payload_dict, skip_bool) using same ‘Lines’ logic as your JE API."""
        # Notes / narration (plain text)
        if move.narration is not False:
            soup = BeautifulSoup(move.narration or '', 'html.parser')
            narration = soup.get_text()
        else:
            narration = False

        journal_entry = {
            'Odoo_id': str(move.id),
            'Date': move.date.strftime('%d-%m-%Y'),
            'Name': move.name,
            'Ref': move.ref,
            'Journal': move.journal_id.name,
            'Notes': narration,
            'Lines': []
        }

        branch = " "
        # For each line, compute CostCenter/State/Company from analytic_distribution
        # If any line lacks required CostCenter/Company -> skip entire entry, as per your logic.
        for line in move.line_ids:
            cos_name = ''
            state_name = ''
            company_name = ''

            # analytic_distribution can contain multiple keys; keep your original approach
            for analytic_id, value in (line.analytic_distribution or {}).items():
                analytic_ids = [int(x) for x in str(analytic_id).split(',') if x.strip()]
                analytic_accounts = request.env['account.analytic.account'].sudo().browse(analytic_ids)
                for aa in analytic_accounts:
                    if aa.exists():
                        cos_name = aa.name or ''
                        state_name = aa.acc_state_id.state_id.name if aa.acc_state_id else ''
                        company_name = aa.nhcl_company_name or ''
                        break
                break  # only first key used (same as your code)

            if not cos_name or not company_name:
                _logger.info(f"Skipping move {move.name} due to missing CostCenter/Company in line {line.id}")
                return None, True  # skip

            # derive Branch from any payable line's partner
            if line.account_id.account_type == 'liability_payable':
                branch = line.partner_id.name
            elif line.account_id.account_type == 'asset_receivable':
                branch = "Cash Customer"
            else:
                branch = " "

            line_dict = {
                'AccountCode': line.account_id.code,
                'AccountName': line.account_id.name,
                'AccountType': line.account_id.account_type,
                'Branch': branch if branch else False,
                'Debit': line.debit,
                'Credit': line.credit,
            }
            if company_name:
                line_dict['Company'] = company_name
            if cos_name:
                line_dict['CostCenter'] = cos_name
            if state_name:
                line_dict['State'] = state_name

            journal_entry['Lines'].append(line_dict)

        if not journal_entry['Lines']:
            _logger.warning(f"Move {move.name} has no line items.")
        return journal_entry, False


    def _response_from_moves(self, moves, wrapper_key):
        """Serialize moves with lines and return a JSON response using wrapper_key."""
        result = []
        for m in moves:
            payload, skip = self._serialize_move_with_lines(m)
            if skip:
                continue
            result.append(payload)

        if not result:
            return request.make_response(json.dumps({"message": "No valid records found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return request.make_response(json.dumps({wrapper_key: result}),
                                     headers=[('Content-Type', 'application/json')], status=200)

    def _invoice_response_from_moves(self, moves, wrapper_key):
        """Serialize moves with lines and return a JSON response using wrapper_key."""
        result = []
        for m in moves:
            payload, skip = self._invoice_serialize_move_with_lines(m)
            if skip:
                continue
            result.append(payload)

        if not result:
            return request.make_response(json.dumps({"message": "No valid records found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return request.make_response(json.dumps({wrapper_key: result}),
                                     headers=[('Content-Type', 'application/json')], status=200)


    @http.route('/odoo/api/get_vendor_bills', type='http', auth='public', methods=['GET'])
    def get_vendor_bills(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('nhcl_tally_flag', '=', 'n'),
        ]
        moves = request.env['account.move'].sudo().search(domain)
        if not moves:
            return request.make_response(json.dumps({"message": "No vendor bills found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._response_from_moves(moves, 'VendorBills')

    @http.route('/odoo/api/get_customer_invoices', type='http', auth='public', methods=['GET'])
    def get_customer_invoices(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('nhcl_tally_flag', '=', 'n'),
        ]
        moves = request.env['account.move'].sudo().search(domain)
        if not moves:
            return request.make_response(json.dumps({"message": "No customer invoices found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._invoice_response_from_moves(moves, 'CustomerInvoices')

    @http.route('/odoo/api/get_vendor_payments', type='http', auth='public', methods=['GET'])
    def get_vendor_payments(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        payments = request.env['account.payment'].sudo().search([
            ('payment_type', '=', 'outbound'),
            ('state', '=', 'paid'),
        ])
        if not payments:
            return request.make_response(json.dumps({"message": "No vendor payments found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # moves = payments.mapped('move_id').sudo().filtered(
        #     lambda m: m.state == 'posted' and getattr(m, 'nhcl_tally_flag', 'n') == 'n'
        # )
        moves = []
        for pay in payments:
            if pay.move_id and pay.move_id.state == 'posted' and pay.move_id.nhcl_tally_flag == 'n':
                moves.append(pay.move_id)
        if not moves:
            return request.make_response(json.dumps({"message": "No vendor payments found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._response_from_moves(moves, 'VendorPayments')

    @http.route('/odoo/api/get_customer_payments', type='http', auth='public', methods=['GET'])
    def get_customer_payments(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        payments = request.env['account.payment'].sudo().search([
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
        ])
        if not payments:
            return request.make_response(json.dumps({"message": "No customer payments found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Filter by move flag if you use nhcl_tally_flag on the journal entry
        moves = []
        for pay in payments:
            if pay.move_id and pay.move_id.state == 'posted' and pay.move_id.nhcl_tally_flag == 'n':
                moves.append(pay.move_id)
        if not moves:
            return request.make_response(json.dumps({"message": "No customer payments  found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._invoice_response_from_moves(moves, 'CustomerPayments')

    @http.route('/odoo/api/update_flag_journal_entries_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_flag_journal_entries_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)])

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
                                'message': f'Voucher number {int(odoo_id)} has been created at tally and the flag updated successfully.'
                            })
                        else:
                            result = json.dumps({
                                'status': "error",
                                'message': f'{int(odoo_id)} Id Record Company Mismatched'
                            })
                        # print("Type:", type(result))
        except Exception as e:
            result = json.dumps({
                'status': "error",
                'message': str(e)
            })

        return result


    def _update_serialize_move_with_lines(self, move):
        """Return (payload_dict, skip_bool) using same ‘Lines’ logic as your JE API."""
        # Notes / narration (plain text)
        if move.narration is not False:
            soup = BeautifulSoup(move.narration or '', 'html.parser')
            narration = soup.get_text()
        else:
            narration = False
        if move.ref:
            ref = move.ref
        else:
            ref = move.name
        if move.line_ids:
            line = move.line_ids[0]
            company_name = ''
            for analytic_id, value in (line.analytic_distribution or {}).items():
                analytic_ids = [int(x) for x in str(analytic_id).split(',') if x.strip()]
                analytic_accounts = request.env['account.analytic.account'].sudo().browse(analytic_ids)

                for analytic_account in analytic_accounts:
                    if analytic_account.exists():
                        company_name = analytic_account.nhcl_company_name or ''
                        break  # break after first valid analytic account
                break

        journal_entry = {
            'Odoo_id': str(move.id),
            'Tally_id': str(move.tally_record_id),
            'Date': move.date.strftime('%d-%m-%Y'),
            'Name': move.name,
            'Ref': move.ref,
            'Journal': move.journal_id.name,
            'Notes': narration,
            'Company': company_name
        }

        return journal_entry, False

    def _update_response_from_moves(self, moves, wrapper_key):
        """Serialize moves with lines and return a JSON response using wrapper_key."""
        result = []
        for m in moves:
            payload, skip = self._update_serialize_move_with_lines(m)
            if skip:
                continue
            result.append(payload)

        if not result:
            return request.make_response(json.dumps({"message": "No valid records found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return request.make_response(json.dumps({wrapper_key: result}),
                                     headers=[('Content-Type', 'application/json')], status=200)


    @http.route('/odoo/api/get_update_vendor_bills', type='http', auth='public', methods=['GET'],csrf=False)
    def get_update_vendor_bills(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('update_flag', '=', 'update'),
        ]
        moves = request.env['account.move'].sudo().search(domain)
        if not moves:
            return request.make_response(json.dumps({"message": "No Update vendor bills found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._update_response_from_moves(moves, 'VendorBills')


    @http.route('/odoo/api/get_update_customer_invoices', type='http', auth='public', methods=['GET'], csrf=False)
    def get_update_customer_invoices(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('update_flag', '=', 'update'),
        ]
        moves = request.env['account.move'].sudo().search(domain)
        if not moves:
            return request.make_response(json.dumps({"message": "No Update customer invoices found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._update_response_from_moves(moves, 'CustomerInvoices')

    @http.route('/odoo/api/get_update_vendor_payments', type='http', auth='public', methods=['GET'],csrf=False)
    def get_update_vendor_payments(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        payments = request.env['account.payment'].sudo().search([
            ('payment_type', '=', 'outbound'),
            ('state', '=', 'paid'),
        ])
        if not payments:
            return request.make_response(json.dumps({"message": "No vendor payments found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)


        moves = []
        for pay in payments:
            if pay.move_id and pay.move_id.state == 'posted' and pay.move_id.update_flag == 'update':
                moves.append(pay.move_id)
        if not moves:
            return request.make_response(json.dumps({"message": "No vendor payments  found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._response_from_moves(moves, 'VendorPayments')

    @http.route('/odoo/api/get_update_customer_payments', type='http', auth='public', methods=['GET'], csrf=False)
    def get_update_customer_payments(self, **kwargs):
        integration, err = self._validation_response(kwargs)
        if err:
            return err

        payments = request.env['account.payment'].sudo().search([
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
        ])
        if not payments:
            return request.make_response(json.dumps({"message": "No Update customer payments found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Filter by move flag if you use nhcl_tally_flag on the journal entry
        moves = []
        for pay in payments:
            if pay.move_id and pay.move_id.state == 'posted' and pay.move_id.update_flag == 'update':
                moves.append(pay.move_id)
        if not moves:
            return request.make_response(json.dumps({"message": "No Update customer payments found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        return self._update_response_from_moves(moves, 'CustomerPayments')

    @http.route('/odoo/api/update_updated_journal_entries_flag_data', type='http', auth='public', methods=['POST'],
                csrf=False)
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
                            'message': f'Voucher number {int(odoo_id)} has been Updated and the update flag updated successfully'
                        })

        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })

        return result

