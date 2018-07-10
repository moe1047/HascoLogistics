# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from openerp.exceptions import ValidationError

class Cargo(models.Model):
    _name = 'logistics.cargo'
    name = fields.Char()
    date_in = fields.Datetime(default=fields.Datetime.now)

    customer_id = fields.Many2one('res.partner', string="Customer",required=True,
        domain=[('logistic_customer', '=', True)])
    memo = fields.Char(string="Memo")
    cargo_detail_ids = fields.One2many(
        'logistics.cargo_detail', 'cargo_id', string="Cargo Detail")
    total_cbm= fields.Float(string='Total CBM',compute='_compute_total_cbm')

    state = fields.Selection([
        ('collected', 'Collected'),
        ('billed', 'Billed'),
        ],default='collected')

    shipment_id = fields.Many2one('logistics.shipment',
        ondelete='set null' ,string="Shipment",required=True)

    billing_id = fields.Many2one('logistics.billing')

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    mark = fields.Char(string="Mark")
    total_rec_qty = fields.Integer(
        string="Total recieved Qty", compute='_get_total_rec_qty', store=True)
    total_repackaged_qty = fields.Integer(
        string="Total repackaged Qty", compute='_get_total_repackaged_qty', store=True)

    shipment_state = fields.Selection([
        ('opened', 'Open'),
        ('closed', 'Close'),
        ],default='opened')

    @api.depends('cargo_detail_ids')
    def _get_total_rec_qty(self):
        for r in self:
            if not r.cargo_detail_ids:
                r.total_rec_qty = 0
            else:
                for cargo_detail in r.cargo_detail_ids:
                    r.total_rec_qty = r.total_rec_qty + cargo_detail.qty
    @api.depends('cargo_detail_ids')
    def _get_total_repackaged_qty(self):
        for r in self:
            if not r.cargo_detail_ids:
                r.total_repackaged_qty = 0
            else:
                for cargo_detail in r.cargo_detail_ids:
                    r.total_repackaged_qty = r.total_repackaged_qty + cargo_detail.repackaged
    @api.model
    def create(self, vals):
        prefix          =   "CC"
        code            =   "logistics.cargo"
        name            =   prefix+"_"+code
        implementation  =   "no_gap"
        padding  =   "3"
        dict            =   { "prefix":prefix,
        "code":code,
        "name":name,
        "active":True,
        "implementation":implementation,
        "padding":padding}
        if self.env['ir.sequence'].search([('code','=',code)]).code == code:
            vals['name'] =  self.env['ir.sequence'].next_by_code('logistics.cargo')
        else:
            new_seq = self.env['ir.sequence'].create(dict)
            vals['name']    =   self.env['ir.sequence'].next_by_code(code)
        result = super(Cargo, self).create(vals)
        return result

    @api.multi
    def unlink(self):
        for cargo in self:
            if cargo.sale_id:
                raise ValidationError('You can not delete a cargo that has a sale!.')

        return super(Cargo, self).unlink()



    @api.multi
    def show_related_sale(self):
        for r in self:
            id=r.billing_id.id
        res = {
           'type': 'ir.actions.act_window',
           'name': 'billing.form',
           'res_model': 'logistics.billing',
           'view_type': 'form',
           'view_mode': 'form',
           'target': 'current',
           'res_id': id,
        }

        return res



    @api.multi
    def sale_order_create(self):

        billing=self.env['logistics.billing']
        billing_line=self.env['logistics.billing_line']
        for column in self:
            customer_id=column.customer_id.id
            date_in=column.date_in
            shipment=column.shipment_id
            company_id=column.company_id.id


        prefix          =   "CB"
        code            =   "logistics.billing"
        name            =   prefix+"_"+code
        implementation  =   "no_gap"
        padding  =   "3"
        dict            =   { "prefix":prefix,
        "code":code,
        "name":name,
        "active":True,
        "implementation":implementation,
        "padding":padding}
        if self.env['ir.sequence'].search([('code','=',code)]).code == code:
            name =  self.env['ir.sequence'].next_by_code('logistics.billing')
        else:
            new_seq = self.env['ir.sequence'].create(dict)
            name    = self.env['ir.sequence'].next_by_code(code)



        #cargo=self.env['logistics.cargo'].create({'name':'new one'})
        inserted_billing=billing.create({
        'date_in':date_in,
        'name':name,
        'customer_id':customer_id,
        'shipment_id':shipment.id,
        'company_id':company_id,

        })


        for column in self:
            for cargo_detail in column.cargo_detail_ids:
                billing_line.create({
                'billing_id':inserted_billing.id,
                'description': str(cargo_detail.item_type.name or '')  + '-'+ str(cargo_detail.memo or '')  +'-'+str(cargo_detail.chasis_no or '')  ,
                'qty':cargo_detail.repackaged,
                'price_unit':cargo_detail.product_id.standard_price,
                'product_id':cargo_detail.product_id.id,
                })
        self.write({
            'state': 'billed',
            'billing_id': inserted_billing.id,
        })
        res = {
           'type': 'ir.actions.act_window',
           'name': 'billing.form',
           'res_model': 'logistics.billing',
           'view_type': 'form',
           'view_mode': 'form',
           'target': 'current',
           'res_id': inserted_billing.id,
        }
        return res

    @api.onchange('customer_id', 'shipment_id')
    def _verify_customer_open_shipment(self):
        shipment = self.env['logistics.shipment'].search([('id','=',self.shipment_id.id)],limit=1)
        if shipment and self.customer_id:
            for cargo in shipment.cargo_ids:
                if cargo.customer_id.id == self.customer_id.id and isinstance(cargo.id, (int, long)):
                    self.customer_id=False
                    return {
                        'warning': {
                            'title': "Duplicate cargo in the same shipment!",
                            'message': "There is already cargo for this customer in this shipment",
                        }
                    }


class CargoDetail(models.Model):
    _name = 'logistics.cargo_detail'
    cargo_id = fields.Many2one('logistics.cargo',
        ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product',string="Service",domain=[('freight', '=', True)] , required=True)

    qty = fields.Integer(string="Recieved Qty",default='')
    rec_qty_uom = fields.Many2one('product.uom',string="UOM", domain=[('freight', '=', True)],required=True)

    repackaged = fields.Float(digits=(6, 4),string="Re-packaged Qty")
    cbm = fields.Float(digits=(6, 4),string="Re-packaged CBM",default=0)
    #unit_price = fields.Float(digits=(6, 4),string="U.Price")
    total_cbm = fields.Float(digits=(6, 4),string="Total CBM", compute='_total_cbm')
    item_type = fields.Many2one('logistics.item_type', string="Description",required=True)
    date = fields.Date(default=datetime.today(),
        string="Date")
    memo = fields.Char(string="Memo")
    chasis_no = fields.Char("Chasis No")
    customer = fields.Char(string="Customer", related='cargo_id.customer_id.name')
    mark = fields.Char(string="Mark", related='cargo_id.mark')



    @api.depends("repackaged","cbm")
    def _total_cbm(self):
        for r in self:
            r.total_cbm = r.repackaged * r.cbm


class Shipment(models.Model):
    _name = 'logistics.shipment'
    name = fields.Char(string="Code",required=True)
    shipping_line_id = fields.Many2one('res.partner',
        ondelete='cascade', domain=[('supplier', '=', True)] ,required=True,string="Shipping Line")
    invoice_ids = fields.One2many(
        'account.invoice', 'shipment_id')
    cargo_ids = fields.One2many(
        'logistics.cargo', 'shipment_id')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    state = fields.Selection([
        ('opened', 'Open'),
        ('closed', 'Close'),
        ],default='opened')

    shipping_type = fields.Selection([
        ('container', 'Container'),
        ('bulk_shipping', 'Bulk Shipping'),
        ],default='container',required=True)


    @api.multi
    def close_shipment(self):
        for r in self:
            for cargo in r.cargo_ids:
                cargo.write({
                    'shipment_state': 'closed',
                })
        self.write({
            'state': 'closed',
        })

class Product(models.Model):
    _inherit = 'product.template'

    # Add a new column to the res.partner model, by default partners are not
    # instructors
    freight = fields.Boolean("Logistic Freight", default=False)

class Partner(models.Model):
    _inherit = 'res.partner'

    # Add a new column to the res.partner model, by default partners are not
    # instructors
    logistic_customer = fields.Boolean("Logistic customer", default=False)


class Invoice(models.Model):
    _inherit = 'account.invoice'


    # Add a new column to the res.partner model, by default partners are not
    # instructors
    shipment_id = fields.Many2one('logistics.shipment',
        ondelete='set null', domain=[('state', '=', 'opened')] ,string="Shipment",required=True)

    consignee_id = fields.Many2one('res.partner',
        ondelete='set null' ,string="Consignee")

    delivered = fields.Boolean("Is delivered", default=False)
    billing_id = fields.Many2one('logistics.billing')


class InvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    # Add a new column to the res.partner model, by default partners are not
    # instructors
    billing_line_id = fields.Many2one('logistics.billing_line')
    # Add a new column to the res.partner model, by default partners are not
    # instructors

class Billing(models.Model):
    _name = 'logistics.billing'
    name = fields.Char()
    date_in = fields.Datetime(default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('logistics.cargo'))


    customer_id = fields.Many2one('res.partner', string="Customer",required=True,help="The person who is paying the bill",domain=[('customer', '=', True)])

    billing_line_ids = fields.One2many(
        'logistics.billing_line', 'billing_id', string="Billing line")


    shipment_id = fields.Many2one('logistics.shipment',
         domain=[('state', '=', 'opened')] ,string="Shipment",required=True)

    invoice_ids = fields.One2many('account.invoice', 'billing_id')
    invoices_count = fields.Integer(
        string="Invoices", compute='_get_invoices_count')
    qty_total = fields.Integer(
        string="Total quantity", compute='_get_total_qty')
    invoiced_total = fields.Integer(
        string="Total invoiced", compute='_get_total_invoiced')
    show_create_invoice=fields.Boolean(
         compute='_show_create_invoice')
    journal_id = fields.Many2one('account.journal',
         domain=[('type', '=', 'sale')] ,string="Journal",required=True,
         default=lambda self: self.env['account.journal'].search([('type','=','sale')],limit=1))

    @api.depends('invoiced_total','qty_total')
    def _show_create_invoice(self):
        for r in self:
            if int(r.qty_total) - int(r.invoiced_total) > 0:
                r.show_create_invoice = True
            else:
                r.show_create_invoice = False

    @api.depends('billing_line_ids.qty','invoice_ids')
    def _get_total_qty(self):
        for r in self:
            for billing_line in r.billing_line_ids:
                r.qty_total = r.qty_total + billing_line.qty
    @api.depends('billing_line_ids.invoiced','invoice_ids','billing_line_ids.delivered')
    def _get_total_invoiced(self):
        for r in self:
            for billing_line in r.billing_line_ids:
                r.invoiced_total = r.invoiced_total + billing_line.invoiced
    @api.depends('invoice_ids')
    def _get_invoices_count(self):
        for r in self:
            r.invoices_count = len(r.invoice_ids)

    @api.multi
    def invoice_create(self):
        invoice=self.env['account.invoice']
        invoice_line=self.env['account.invoice.line']
        #company=self.env['res.company']._company_default_get('account.invoice')

        for column in self:
            customer_id=column.customer_id.id
            date_in=column.date_in
            origin=column.name
            billing_id=column.id
            shipment_id=column.shipment_id.id

            invoiced_total=column.invoiced_total
            qty_total=column.qty_total
            company=column.company_id
            journal_id=column.journal_id.id

        if int(qty_total-invoiced_total) == 0:
            raise ValidationError('Nothing to invoice')



        inserted_invoice=invoice.create({
        'origin':origin,
        'partner_id':customer_id,
        'journal_id':journal_id,
        'date_invoice':date_in,
        'account_id':self.env['res.partner'].search([('id','=',customer_id)]).property_account_receivable_id.id,
        'company_id':company.id,
        'currency_id':company.currency_id.id,
        'billing_id':billing_id,
        'shipment_id':shipment_id,

        })


        for column in self:
            for billing_line in column.billing_line_ids:
                if int(billing_line.qty)-int(billing_line.invoiced) > 0:
                    invoice_line.create({
                    'name':str(billing_line.description),
                    'invoice_id':inserted_invoice.id,
                    'account_id':self.env['product.template'].search([('id','=',billing_line.product_id.id)]).property_account_income_id.id or self.env['product.template'].search([('id','=',billing_line.product_id.id)]).categ_id.property_account_income_categ_id.id,
                    'price_unit':billing_line.unit_price,
                    'quantity':int(billing_line.qty-billing_line.invoiced),
                    'billing_line_id':billing_line.id,
                    })


        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
        action['res_id'] = inserted_invoice.id
        return action

    @api.multi
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action




class BillingLine(models.Model):
    _name = 'logistics.billing_line'
    billing_id = fields.Many2one('logistics.billing',
        ondelete='set null', required=True)
    product_id = fields.Many2one('product.product',string="CBM/KGS/UNITS",domain=[('freight', '=', True)] , required=True)
    invoice_line_ids = fields.One2many('account.invoice.line', 'billing_line_id')
    description = fields.Text(string="Description", required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('logistics.cargo'))

    qty = fields.Integer(string="Recieved Qty")
    delivered = fields.Integer(string="Delivered",compute='_compute_delivered')
    invoiced = fields.Integer(string="Invoiced",compute='_compute_invoiced')
    unit_price = fields.Float(string="U.price")
    amount = fields.Integer(
        string="Total", compute='_calculate_amount', store=True)


    @api.depends('qty','unit_price')
    def _calculate_amount(self):
        for r in self:
            r.amount=r.qty*r.unit_price
    @api.depends('billing_id.invoice_ids')
    def _compute_delivered(self):
        for r in self:
            for invoice_line in r.invoice_line_ids:
                r.delivered=r.delivered+invoice_line.quantity
    @api.depends('invoice_line_ids')
    def _compute_invoiced(self):
        for r in self:
            for invoice_line in r.invoice_line_ids:
                r.invoiced=r.invoiced+invoice_line.quantity

class ReportManifest(models.AbstractModel):
    _name = "report.kalkaal_logistics.manifest_report"


    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        #report_obj = self.env['report']
        #report = report_obj._get_report_from_name('kalkaal_logistics.report_manifest_template')
        invoices = self.env['account.invoice'].search([('shipment_id', '=', docs.shipment_id.id),
        ('state', '!=', 'draft'),('state', '!=', 'cancel')])
        #orders = self.env['sale.order'].search([('shipment_id', '=', docs.shipment_id.id)])

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'data':invoices,
        }
        return self.env['report'].render('kalkaal_logistics.manifest_report', docargs)

class ManifestWizard(models.TransientModel):
    _name = "logistics.manifest_wizard"
    _description = "Salesperson wizard"

    shipment_id = fields.Many2one('logistics.shipment',
        ondelete='cascade',string="Select Shipment",required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    #date_from = fields.Datetime(string='Start Date')
    #date_to = fields.Datetime(string='End Date')
    @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['shipment_id'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['shipment_id'])[0])
        return self.env['report'].get_action(self, 'kalkaal_logistics.manifest_report', data=data)
class ItemType(models.Model):
    _name = 'logistics.item_type'
    name = fields.Char(string="Description",required=True)

class ProductUOM(models.Model):
    _inherit = 'product.uom'

    # Add a new column to the res.partner model, by default partners are not
    # instructors
    freight = fields.Boolean("Freight UOM", default=False)
   # Define fields according to your need

class BillingLine(models.Model):
    _name = 'logistics.billing_line'
    billing_id = fields.Many2one('logistics.billing',
        ondelete='set null', required=True)
    product_id = fields.Many2one('product.product',string="CBM/KGS/UNITS",domain=[('freight', '=', True)] , required=True)
    invoice_line_ids = fields.One2many('account.invoice.line', 'billing_line_id')
    description = fields.Text(string="Description", required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('logistics.cargo'))

    qty = fields.Integer(string="Recieved Qty")
    delivered = fields.Integer(string="Delivered",compute='_compute_delivered')
    invoiced = fields.Integer(string="Invoiced",compute='_compute_invoiced')
    unit_price = fields.Float(string="U.price")
    amount = fields.Integer(
        string="Total", compute='_calculate_amount', store=True)

    @api.depends('qty','unit_price')
    def _calculate_amount(self):
        for r in self:
            r.amount=r.qty*r.unit_price
    @api.depends('billing_id.invoice_ids')
    def _compute_delivered(self):
        for r in self:
            for invoice_line in r.invoice_line_ids:
                r.delivered=r.delivered+invoice_line.quantity
    @api.depends('invoice_line_ids')
    def _compute_invoiced(self):
        for r in self:
            for invoice_line in r.invoice_line_ids:
                r.invoiced=r.invoiced+invoice_line.quantity
