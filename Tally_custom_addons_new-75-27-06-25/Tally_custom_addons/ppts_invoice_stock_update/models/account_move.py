from odoo.exceptions import UserError
from odoo import models, fields, _, api


class AccountMove(models.Model):
    """account.move model to stock.picking value are created in delivery and receipt"""
    _inherit = 'account.move'

    def _get_stock_type_ids(self):
        """Default value function: This will determine picking type of incoming shipment"""
        data = self.env['stock.picking.type'].search([])
        if self._context.get('default_move_type') == 'out_invoice':
            for line in data:
                if line.code == 'outgoing':
                    return line
        if self._context.get('default_move_type') == 'in_invoice':
            for line in data:
                if line.code == 'incoming':
                    return line
        if self._context.get('default_move_type') == 'out_refund':
            for line in data:
                if line.code == 'incoming':
                    return line
        if self._context.get('default_move_type') == 'in_refund':
            for line in data:
                if line.code == 'outgoing':
                    return line

    def _default_picking_transfer(self):
        """Default value function: This will determine picking type of outgoing shipment"""
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.company.id
        types = type_obj.search([('code', '=', 'outgoing'),
                                 ('warehouse_id.company_id', '=', company_id)], limit=1)
        if not types:
            types = type_obj.search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        return types[:4]

    picking_count = fields.Integer(string="Count", compute='_compute_picking_count')
    picking_shipment_count = fields.Integer(string="Count", compute='_compute_shipment_count')
    invoice_picking_id = fields.Many2one('stock.picking', string="Picking Id")
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type',
                                      default=_get_stock_type_ids,
                                      help="This will determine picking type of incoming shipment")
    picking_transfer_id = fields.Many2one('stock.picking.type', 'Deliver To', required=True,
                                          default=_default_picking_transfer,
                                          help="This will determine picking type of outgoing shipment")
    picking_deliver = fields.Boolean(string="Deliver", compute='_compute_picking_deliver')
    picking_deliver_bill = fields.Boolean(string="Deliver", compute='_compute_picking_deliver_bill')
    deliver_no = fields.Boolean(string="Deliver No", compute='_compute_picking_deliver_no')
    deliver_shipment_no = fields.Boolean(string="Deliver No", compute='_compute_shipment_deliver_no')
    deliver_status = fields.Selection([
        ('delivered', 'Delivered'),
        ('partially', 'Partially Delivered'),
         ], string='Deliver Status', readonly=True, track_visibility='always')
    shipment_status = fields.Selection([
        ('received', 'Received'),
        ('partially', 'Partially Received'),
         ], string='Shipment Status', readonly=True, track_visibility='always')
    states = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
        ('done', 'Received')],
        string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)
    picking_ids = fields.One2many('stock.picking', 'invoice_id',
                                  string="Pickings", readonly=True, copy=False)

    def _compute_deliver_status(self):
        """This method computes the delivery status based on the picking count and name of the record.
        If there are pending pickings related to the record, it sets the deliver_status to 'partially'.
        Otherwise, it sets the deliver_status to 'delivered'."""
        if self.picking_count > 0 and self.name:
            picking_type_state = self.env['stock.picking'].search([('origin', '=', self.name),
                                                                   ('state', '!=', 'done')])
            if picking_type_state:
                self.deliver_status = 'partially'
            else:
                self.deliver_status = 'delivered'
                    
    def _compute_shipment_status(self):
        """ This method computes the shipment status based on the shipment count and name of the record.
        If there are pending shipments related to the record, it sets the shipment_status to 'partially'.
        Otherwise, it sets the shipment_status to 'received'."""
        if self.picking_shipment_count > 0 and self.name:
            picking_type_state = self.env['stock.picking'].search([('origin', '=', self.name),
                                                                   ('state', '!=', 'done')])
            if picking_type_state:
                self.shipment_status = 'partially'
            else:
                self.shipment_status = 'received'

    def button_draft(self):
        """ Override the button_draft method of AccountMove to handle draft status actions.
        This method sets the invoice line product quantity fields as read-only if there are
        related pickings or shipments.:return: Result of calling the superclass method button_draft()."""
        res = super(AccountMove, self).button_draft()
        for move in self:
            if move.picking_count > 0:
                move.invoice_line_ids.readonly_product_quantity = True
            if move.picking_shipment_count > 0:
                move.invoice_line_ids.readonly_product_quantity = True
        return res

    def action_stock_receive(self):
        """
        Perform actions related to stock receiving for the invoice.
        If the company's configuration allows creating stock pickings from invoices:
        - Check if there are invoice lines; if not, raise an error.
        - Ensure the invoice has a name; if not, raise an error.
        - If no related picking exists:
            - If there's only one invoice line and it represents a service, raise an error.
            - Create a new stock picking based on invoice details.
            - Update invoice's invoice_picking_id and picking_count fields.
            - Create stock moves for applicable product lines and confirm them.
        Update the shipment status based on related pickings.
        :return: True if stock picking from invoice is not enabled for the company."""
        if self.company_id.stock_picking_bill:
            for order in self:
                if not order.invoice_line_ids:
                    raise UserError(_('Please create some invoice lines.'))
                if not self.name:
                    raise UserError(_('Please Validate invoice.'))
                if not self.invoice_picking_id:
                    if (len(order.invoice_line_ids) == 1 and
                            order.invoice_line_ids.product_id.detailed_type == 'service'):
                        raise UserError(_('The system will not generate a product Type as'
                                          ' "Service" for order creation of delivery/shipment.'))
                    pick = {
                        'picking_type_id': self.picking_type_id.id,
                        'partner_id': self.partner_id.id,
                        'origin': self.name,
                        'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                        'location_id': self.partner_id.property_stock_supplier.id,
                        'move_type': 'direct',
                        'invoice_id': order.id,
                    }
                    picking = self.env['stock.picking'].create(pick)
                    self.invoice_picking_id = picking.id
                    self.picking_count = len(picking)
                    moves = order.invoice_line_ids.filtered(
                        lambda r: r.product_id.type in ['product', 'consu']
                                  and r.product_id.type != 'service'). \
                        _create_stock_moves(picking)
                    move_ids = moves._action_confirm()
                    move_ids._action_assign()
                    picking.button_validate()
        else:
            return True
        if self.picking_shipment_count > 0 and self.name:
            picking_type_state = self.env['stock.picking'].search([('origin', '=', self.name),
                                                                   ('state', '!=', 'done')])
            if picking_type_state:
                self.shipment_status = 'partially'
            else:
                self.shipment_status = 'received'
    
    def _compute_picking_deliver_bill(self):
        """Compute the picking delivery bill based on the company's stock picking configuration.
        If the company allows creating stock pickings from invoices, set picking_deliver_bill to True.
        Otherwise, set it to False."""
        if self.company_id.stock_picking_bill:
            self.picking_deliver_bill = True
        else:
            self.picking_deliver_bill = False 
                
    def _compute_picking_deliver(self):
        """Compute the picking delivery based on the company's stock picking configuration.
        If the company allows creating stock pickings, set picking_deliver to True.
        Otherwise, set it to False."""
        if self.company_id.stock_picking:
            self.picking_deliver = True
        else:
            self.picking_deliver = False    
    
    def _compute_picking_deliver_no(self):
        """ Compute the delivery status based on the picking count.
        If there are pickings associated with the record, set deliver_no to True.
        Otherwise, set it to False."""
        if self.picking_count > 0:
            self.deliver_no = True
        else:
            self.deliver_no = False

    def _compute_shipment_deliver_no(self):
        """Compute the delivery status based on the shipment count.
        If there are shipments associated with the record, set deliver_shipment_no to True.
        Otherwise, set it to False."""
        if self.picking_shipment_count > 0:
            self.deliver_shipment_no = True
        else:
            self.deliver_shipment_no = False

    def action_stock_transfer(self):
        """ Perform actions related to stock transfer.
        If the company's configuration allows creating stock pickings:
        - Check if there are invoice lines; if not, raise an error.
        - Ensure the invoice has a name; if not, raise an error.
        - If no related picking exists:
            - If there's only one invoice line and it represents a service, raise an error.
            - Create a new stock picking based on invoice details for transfer.
            - Update invoice's invoice_picking_id and picking_count fields.
            - Create stock moves for applicable product lines and confirm them.
        Update the deliver status based on related pickings.
        :return: True if stock transfer from invoice is not enabled for the company."""
        if self.company_id.stock_picking:
            for order in self:
                if not order.invoice_line_ids:
                    raise UserError(_('Please create some invoice lines.'))
                if not self.name:
                    raise UserError(_('Please Validate invoice.'))
                if not self.invoice_picking_id:
                    if (len(order.invoice_line_ids) == 1 and order
                            .invoice_line_ids.product_id.detailed_type == 'service'):
                        raise UserError(_('The system will not generate a product Type '
                                          'as "Service" for order creation of delivery/shipment.'))
                    pick = {
                        'picking_type_id': self.picking_transfer_id.id,
                        'partner_id': self.partner_id.id,
                        'origin': self.name,
                        'location_dest_id': self.partner_id.property_stock_customer.id,
                        'location_id': self.picking_transfer_id.default_location_src_id.id,
                        'move_type': 'direct',
                        'invoice_id': order.id,
                    }
                    picking = self.env['stock.picking'].create(pick)
                    print(picking)
                    self.invoice_picking_id = picking.id
                    self.picking_count = len(picking)
                    moves = order.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu']
                                    and r.product_id.type != 'service')._create_stock_moves_transfer(picking)
                    move_ids = moves._action_confirm()
                    move_ids._action_assign()
                    picking.button_validate()
        else:
            return True
        if self.picking_count > 0:
            picking_type_state = self.env['stock.picking'].search([('origin', '=', self.name),
                                                                   ('state', '!=', 'done')])
            if picking_type_state:
                self.deliver_status = 'partially'
            else:
                self.deliver_status = 'delivered'

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' #Overwrite
        Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.
        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if self.picking_type_id.code == 'outgoing':
            data = self.env['stock.picking.type'].search(
                [('company_id', '=', self.company_id.id), ('code', '=', 'incoming')], limit=1)
            self.picking_type_id = data.id
            self.invoice_picking_id = None

        elif self.picking_type_id.code == 'incoming':
            data = self.env['stock.picking.type'].search(
                [('company_id', '=', self.company_id.id), ('code', '=', 'outgoing')], limit=1)
            self.picking_type_id = data.id
            self.invoice_picking_id = None
        reverse_moves = super(AccountMove, self)._reverse_moves(
            default_values_list=default_values_list, cancel=cancel)
        return reverse_moves

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        """Compute the number of pickings associated with each invoice."""
        for invoice in self:
            invoice.picking_count = len(invoice.picking_ids)

    @api.depends('picking_ids')
    def _compute_shipment_count(self):
        """Compute the number of shipments associated with each invoice."""
        for invoice in self:
            invoice.picking_shipment_count = len(invoice.picking_ids)

    def action_view_picking_delivery(self):
        """Action to view the pickings associated with the delivery.
        :return: Action to view the pickings associated with the delivery."""
        return self._get_action_view_picking(self.picking_ids)

    def action_view_picking_shipment(self):
        """Action to view the pickings associated with the shipment.
        :return: Action to view the pickings associated with the shipment."""
        return self._get_action_view_picking(self.picking_ids)

    def _get_action_view_picking(self, pickings):
        """Get the action to view pickings.
        :param pickings: Pickings associated with the record.
        :return: Action to view pickings."""
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for
                                               state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id

        # Prepare the context.
        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]

        action['context'] = dict(
            self._context,
            default_partner_id=self.partner_id.id,
            default_picking_type_id=picking_id.picking_type_id.id,
            default_origin=self.name,
            default_group_id=picking_id.group_id.id,
        )
        return action


class AccountMoveLine(models.Model):
    """Account Move Line add new field to stock update"""
    _inherit = 'account.move.line'

    readonly_product_quantity = fields.Boolean(string="Readonly Product and Quantity")

    def _create_stock_moves(self, picking):
        """Create stock moves for the given picking.
        :param picking: Stock picking for which moves are to be created.
        :return: Stock moves created for the picking."""
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'location_id': line.move_id.partner_id.property_stock_supplier.id,
                'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                'picking_id': picking.id,
                'state': 'draft',
                'company_id': line.move_id.company_id.id,
                'price_unit': price_unit,
                'quantity': line.quantity,  # custom
                'picking_type_id': picking.picking_type_id.id,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done

    def _create_stock_moves_transfer(self, picking):
        """Create stock moves for transfer picking.
        :param picking: Stock picking for which moves are to be created.
        :return: Stock moves created for the picking."""
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'location_id': picking.picking_type_id.default_location_src_id.id,
                'location_dest_id': line.move_id.partner_id.property_stock_customer.id,
                'picking_id': picking.id,
                'state': 'draft',
                'company_id': line.move_id.company_id.id,
                'price_unit': price_unit,
                'quantity': line.quantity, #custom
                'picking_type_id': picking.picking_type_id.id,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done
