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
        ('billed', 'Service Ordered'),
        ],default='collected')

    shipment_id = fields.Many2one('logistics.shipment',
        ondelete='set null' ,string="Shipment",required=True,domain=[('state', '=', 'opened')])

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
    receivable_id = fields.Many2one('account.account', string='Logistic Account Recievable',
    domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",default=lambda self:self.env['account.account'].search([('id','=',self.env['ir.values'].get_default('logistics.config.settings', 'logistic_recievables_id'))],limit=1))
    payable_id = fields.Many2one('account.account', string='Logistic Account Payable',
    domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",default=lambda self:self.env['account.account'].search([('id','=',self.env['ir.values'].get_default('logistics.config.settings', 'logistic_payable_id'))],limit=1))



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
            if cargo.billing_id:
                raise ValidationError('You can not delete a cargo that has a service order!.')

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
            mark=column.mark
            source=column.name

        for column in self:
            cargo_detail_ids=column.cargo_detail_ids

        for cargo_detail in cargo_detail_ids:
            if cargo_detail.repackaged == 0 and cargo_detail.product_id.name != '+':
                return {
                    'warning': {
                        'title': "Fill repackaged quantity!",
                        'message': "Some of the services are filled but not the related repackaged quantity",
                    }
                }


            if cargo_detail.repackaged > 0 and cargo_detail.product_id.name == '+':
                return {
                    'warning': {
                        'title': "Fill service cell!",
                        'message': "Some of the repackaged quantity are filled but not the related service",
                    }
                }




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
        'currency_id':131,
        'date_in':date_in,
        'name':name,
        'source':source,
        'mark':mark,
        'customer_id':customer_id,
        'shipment_id':shipment.id,
        'company_id':company_id,

        })


        for column in self:
            for cargo_detail in column.cargo_detail_ids:
                item_type_desc=''

                for item_type in cargo_detail.item_types:
                    item_type_desc = item_type_desc +" "+item_type.name
                memo=''
                if cargo_detail.memo:
                    memo='/ '+cargo_detail.memo

                if cargo_detail.repackaged != 0 and cargo_detail.product_id.name != '+':
                    billing_line.create({
                    'billing_id':inserted_billing.id,
                    'description': str(item_type_desc)+memo ,
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
    @api.onchange('cargo_detail_ids')
    def _verify_cargo_detail_ids(self):
        for column in self:
            cargo_detail_ids=column.cargo_detail_ids

        for cargo_detail in cargo_detail_ids:
            if cargo_detail.repackaged == 0 and cargo_detail.product_id.name != '+':
                return {
                    'warning': {
                        'title': "Fill repackaged quantity!",
                        'message': "Some of the services are filled but not the related repackaged quantity",
                    }
                }


            if cargo_detail.repackaged > 0 and cargo_detail.product_id.name == '+':
                return {
                    'warning': {
                        'title': "Fill service cell!",
                        'message': "Some of the repackaged quantity are filled but not the related service",
                    }
                }


class CargoDetail(models.Model):
    _name = 'logistics.cargo_detail'
    cargo_id = fields.Many2one('logistics.cargo',
        ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product',string="Service",domain=[('freight', '=', True)] )

    qty = fields.Integer(string="Recieved Qty",default='')
    rec_qty_uom = fields.Many2one('product.uom',string="UOM",required=True)

    repackaged = fields.Float(digits=(6, 4),string="Re-packaged Qty")
    cbm = fields.Float(digits=(6, 4),string="Re-packaged CBM",default=0)
    #unit_price = fields.Float(digits=(6, 4),string="U.Price")
    total_cbm = fields.Float(digits=(6, 4),string="Total CBM", compute='_total_cbm')
    item_types = fields.Many2many('logistics.item_type', string="Description",required=True)
    date = fields.Date(default=fields.Datetime.now,
        string="Date")
    memo = fields.Char(string="Memo")
    customer = fields.Char(string="Customer", related='cargo_id.customer_id.name')
    mark = fields.Char(string="Mark", related='cargo_id.mark')




    @api.depends("repackaged","cbm")
    def _total_cbm(self):
        for r in self:
            r.total_cbm = r.repackaged * r.cbm


class Shipment(models.Model):
    _name = 'logistics.shipment'
    name = fields.Char(string="Code",required=True)
    invoice_ids = fields.One2many(
        'account.invoice', 'shipment_id')
    cargo_ids = fields.One2many(
        'logistics.cargo', 'shipment_id',)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    state = fields.Selection([
        ('opened', 'Open'),
        ('closed', 'Close'),
        ],default='opened')

    shipping_type = fields.Selection([
        ('container', 'Container'),
        ('bulk_shipping', 'Bulk Shipping'),
        ],default='container',required=True)
    account_analytic_id = fields.Many2one('account.analytic.account',
        string='Analytic Account',required=True)


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
        ondelete='set null', domain=[('state', '=', 'opened')] ,string="Shipment")

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
    mark = fields.Char(string="Mark")
    source = fields.Char(string="Source")
    billing_line_ids = fields.One2many(
        'logistics.billing_line', 'billing_id', string="Billing line")

    shipment_id = fields.Many2one('logistics.shipment',
        ondelete='set null' ,string="Shipment",required=True,domain=[('state', '=', 'opened')])

    invoice_ids = fields.One2many('account.invoice', 'billing_id')
    local_invoice_id = fields.Many2one('account.invoice', 'billing_id')

    invoices_count = fields.Integer(
        string="Invoices", compute='_get_invoices_count')
    local_invoices_count = fields.Integer(
        string="Invoices", compute='_get_local_invoices_count')
    qty_total = fields.Integer(
        string="Total quantity", compute='_get_total_qty')
    invoiced_total = fields.Integer(
        string="Total invoiced", compute='_get_total_invoiced')
    show_create_invoice=fields.Boolean(
         compute='_show_create_invoice')

    user_id = fields.Many2one('res.users',
        string="Sale Person",required=True,default=lambda self: self.env.user)
    currency_id = fields.Many2one('res.currency',
        ondelete='set null',default=lambda self:self.company_id.currency_id)
    invoice_status = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('to_invoice', 'To Invoice'),
        ], string='Invoice Status', compute='_get_invoiced', store=True, readonly=True)
    @api.depends('billing_line_ids.invoice_status')
    def _get_invoiced(self):
        for billing in self:
            invoice_status = 'invoiced'
            for billing_line in billing.billing_line_ids:
                if billing_line.invoice_status == 'to_invoice':
                    invoice_status = 'to_invoice'
                    break

            billing.update({
                'invoice_status': invoice_status,
            })


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
    @api.depends('local_invoice_id')
    def _get_local_invoices_count(self):
        for r in self:
            r.local_invoices_count = len(r.local_invoice_id)

    @api.multi
    def invoice_create(self):
        invoice=self.env['account.invoice']
        invoice_line=self.env['account.invoice.line']
        #company=self.env['res.company']._company_default_get('account.invoice')

        for column in self:
            ir_values = self.env['ir.values']
            team_id = ir_values.get_default('logistics.config.settings', 'team_id')
            journal_id = ir_values.get_default('logistics.config.settings', 'journal_id')

            customer_id=column.customer_id.id
            date_in=column.date_in
            origin=column.name
            billing_id=column.id
            shipment_id=column.shipment_id.id

            invoiced_total=column.invoiced_total
            qty_total=column.qty_total
            company=column.company_id
            user_id=column.user_id.id
            currency_id=column.currency_id.id
            mark=column.mark

        if int(qty_total-invoiced_total) == 0:
            raise ValidationError('Nothing to invoice')

        inserted_invoice=invoice.create({
        'origin':origin,
        'partner_id':customer_id,
        'name':mark,
        'shipment_id':shipment_id,
        'journal_id':journal_id,
        'date_invoice':date_in,
        'account_id':self.env['res.partner'].search([('id','=',customer_id)]).property_account_receivable_id.id,
        'company_id':company.id,
        'currency_id':company.currency_id.id,
        'billing_id':billing_id,
        'shipment_id':shipment_id,
        'team_id':team_id,
        'user_id':user_id,
        'currency_id':currency_id,
        })


        for column in self:
            for billing_line in column.billing_line_ids:
                if int(billing_line.qty)-int(billing_line.invoiced) > 0:
                    invoice_line.create({
                    'product_id':billing_line.product_id.id,
                    'name':str(billing_line.description),
                    'account_analytic_id':column.shipment_id.account_analytic_id.id,
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
    def local_invoice_create(self):

        invoice=self.env['account.invoice']
        invoice_line=self.env['account.invoice.line']
        #company=self.env['res.company']._company_default_get('account.invoice')

        for column in self:
            ir_values = self.env['ir.values']
            team_id = ir_values.get_default('logistics.config.settings', 'local_team_id')
            journal_id = ir_values.get_default('logistics.config.settings', 'journal_id')
            income_account_id = ir_values.get_default('logistics.config.settings', 'service_income_account_id')

            customer_id=column.customer_id.id
            date_in=column.date_in
            origin=column.name
            billing_id=column.id
            shipment_id=column.shipment_id.id

            invoiced_total=column.invoiced_total
            qty_total=column.qty_total
            company=column.company_id
            user_id=column.user_id.id


        inserted_invoice=invoice.create({
        'origin':origin,
        'partner_id':customer_id,
        'journal_id':journal_id,
        'date_invoice':date_in,
        'account_id':self.env['res.partner'].search([('id','=',customer_id)]).property_account_receivable_id.id,
        'company_id':company.id,
        'shipment_id':shipment_id,
        'team_id':team_id,
        'user_id':user_id,
        })

        for column in self:
            for billing_line in column.billing_line_ids:
                invoice_line.create({
                'product_id':billing_line.product_id.id,
                'name':str(billing_line.description),
                'account_analytic_id':column.shipment_id.account_analytic_id.id,
                'invoice_id':inserted_invoice.id,
                'account_id':income_account_id,
                'price_unit':0,
                'quantity':billing_line.qty,
                })
            column.update({
                'local_invoice_id': inserted_invoice.id,
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

    @api.multi
    def action_view_local_invoice(self):
        invoices = self.mapped('local_invoice_id')
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
    product_id = fields.Many2one('product.product',string="Service",domain=[('freight', '=', True)] , required=True)
    invoice_line_ids = fields.One2many('account.invoice.line', 'billing_line_id')
    description = fields.Text(string="Description", required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('logistics.cargo'))

    qty = fields.Integer(string="Recieved Qty")
    delivered = fields.Integer(string="Delivered",compute='_compute_delivered', store=True)
    invoiced = fields.Integer(string="Invoiced",compute='_compute_invoiced', store=True)
    unit_price = fields.Float(string="U.price")
    amount = fields.Integer(
        string="Total", compute='_calculate_amount', store=True)

    customer = fields.Char(string="Customer", related='billing_id.customer_id.name')
    shipment = fields.Char(string="Shipment", related='billing_id.shipment_id.name')
    invoice_status = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('to_invoice', 'To Invoice'),
        ], string='Invoice Status', compute='_compute_invoice_status', store=True, readonly=True,default='to_invoice')


    @api.depends('invoice_status', 'invoiced', 'qty')
    def _compute_invoice_status(self):
        for line in self:
            if line.qty != line.invoiced:
                line.invoice_status = 'to_invoice'
            elif line.qty == line.invoiced:
                line.invoice_status = 'invoiced'



    @api.depends('qty','unit_price')
    def _calculate_amount(self):
        for r in self:
            r.amount=r.qty*r.unit_price



    @api.depends('invoice_line_ids','invoice_line_ids.quantity','billing_id.invoice_ids.invoice_line_ids.quantity')
    def _compute_delivered(self):
        for r in self:
            for invoice_line in r.invoice_line_ids:
                r.delivered=r.delivered+invoice_line.quantity



    @api.depends('invoice_line_ids','invoice_line_ids.quantity','billing_id.invoice_ids.invoice_line_ids.quantity')
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
        if docs.category_id:
            products=self.env['product.product'].search([('categ_id', '=', docs.category_id.id)]).ids
        else:
            products=self.env['product.product'].search([]).ids

        if docs.customer_id:
            customers=self.env['res.partner'].search([('id', '=', docs.customer_id.id)]).ids
        else:
            customers=self.env['res.partner'].search([]).ids

        if docs.team_id:
            teams=self.env['crm.team'].search([('id', '=', docs.team_id.id)]).ids
        else:
            teams=self.env['crm.team'].search([]).ids


        if docs.product_id:
            product=self.env['product.product'].search([('id', '=', docs.product_id.id)]).ids
        else:
            product=self.env['product.product'].search([]).ids

        #report_obj = self.env['report']
        #report = report_obj._get_report_from_name('kalkaal_logistics.report_manifest_template')
        invoices = self.env['account.invoice.line'].search([('account_analytic_id', '=', docs.shipment_id.account_analytic_id.id),
        ('product_id', 'in', products),('product_id', 'in', product),('invoice_id.partner_id', 'in', customers),('invoice_id.team_id', 'in', teams)])
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
    _description = "Manifest wizard"

    shipment_id = fields.Many2one('logistics.shipment',
        string="Select Shipment",required=True)
    category_id = fields.Many2one('product.category',
        string="Category")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    customer_id = fields.Many2one('res.partner',string="Customer")
    team_id = fields.Many2one('crm.team', string='Sales Team')
    product_id = fields.Many2one('product.product',string="Service",domain=[('freight', '=', True)] , required=True)
    #date_from = fields.Datetime(string='Start Date')
    #date_to = fields.Datetime(string='End Date')
    @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['shipment_id','category_id','customer_id','team_id','product_id'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['shipment_id','category_id','customer_id','team_id','product_id'])[0])
        return self.env['report'].get_action(self, 'kalkaal_logistics.manifest_report', data=data)
class ReportSummaryManifest(models.AbstractModel):
    _name = "report.kalkaal_logistics.manifest_summary_report"


    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        if docs.category_id:
            products=self.env['product.product'].search([('categ_id', '=', docs.category_id.id)]).ids
        else:
            products=self.env['product.product'].search([]).ids

        if docs.customer_id:
            customers=self.env['res.partner'].search([('id', '=', docs.customer_id.id)]).ids
        else:
            customers=self.env['res.partner'].search([]).ids

        if docs.team_id:
            teams=self.env['crm.team'].search([('id', '=', docs.team_id.id)]).ids
        else:
            teams=self.env['crm.team'].search([]).ids

        #report_obj = self.env['report']
        #report = report_obj._get_report_from_name('kalkaal_logistics.report_manifest_template')
        invoices = self.env['account.invoice.line'].search([('account_analytic_id', '=', docs.shipment_id.account_analytic_id.id),
        ('product_id', 'in', products),('invoice_id.partner_id', 'in', customers),('invoice_id.team_id', 'in', teams)])
        #orders = self.env['sale.order'].search([('shipment_id', '=', docs.shipment_id.id)])

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'data':invoices,
        }
        return self.env['report'].render('kalkaal_logistics.manifest_summary_report', docargs)
class ManifestSummaryWizard(models.TransientModel):
    _name = "logistics.manifest_summary_wizard"
    _description = "Manifest Summary wizard"

    shipment_id = fields.Many2one('logistics.shipment',
        string="Select Shipment",required=True)
    category_id = fields.Many2one('product.category',
        string="Category")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    customer_id = fields.Many2one('res.partner',string="Customer")
    team_id = fields.Many2one('crm.team', string='Sales Team')
    #date_from = fields.Datetime(string='Start Date')
    #date_to = fields.Datetime(string='End Date')
    @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['shipment_id','category_id','customer_id','team_id'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['shipment_id','category_id','customer_id','team_id'])[0])
        return self.env['report'].get_action(self, 'kalkaal_logistics.manifest_summary_report', data=data)

class ItemType(models.Model):
    _name = 'logistics.item_type'
    name = fields.Char(string="Description",required=True)


class LogisticsSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'logistics.config.settings'
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    journal_id = fields.Many2one('account.journal', string='Journal ',domain=[('type', '=', 'sale')])
    team_id = fields.Many2one('crm.team', string='Sales Team')
    local_team_id = fields.Many2one('crm.team', string='Local Team')
    logistic_recievables_id = fields.Many2one('account.account', string='Logistic Account Recievable',
    domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]")
    logistic_payable_id = fields.Many2one('account.account', string='Logistic Account Payable',
    domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]")
    service_income_account_id=fields.Many2one('account.account', string='Service Income Account',
    domain="[ ('deprecated', '=', False)]")
    @api.multi
    def set_team_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'logistics.config.settings', 'team_id', self.team_id.id)
    @api.multi
    def set_journal_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'logistics.config.settings', 'journal_id', self.journal_id.id)
    @api.multi
    def set_local_team_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'logistics.config.settings', 'local_team_id', self.local_team_id.id)
    @api.multi
    def set_logistic_recievables_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'logistics.config.settings', 'logistic_recievables_id', self.logistic_recievables_id.id)
    @api.multi
    def set_logistic_payable_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'logistics.config.settings', 'logistic_payable_id', self.logistic_payable_id.id)

    @api.multi
    def set_service_income_account_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'logistics.config.settings', 'service_income_account_id', self.service_income_account_id.id)

class ReportCargo(models.AbstractModel):
    _name = "report.kalkaal_logistics.cargo_report"


    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))

        if docs.state:
            state=[docs.state]
        else:
            state=['collected','billed']

        if docs.customer_id:
            customers=self.env['res.partner'].search([('id', '=', docs.customer_id.id)]).ids
        else:
            customers=self.env['res.partner'].search([]).ids

        if docs.shipment_id:
            shipment_ids=[docs.shipment_id.id]
        else:
            shipment_ids=self.env['logistics.shipment'].search([]).ids

        #report_obj = self.env['report']
        #report = report_obj._get_report_from_name('kalkaal_logistics.report_manifest_template')
        cargos = self.env['logistics.cargo_detail'].search([('cargo_id.shipment_id', 'in', shipment_ids),
        ('cargo_id.customer_id', 'in', customers),('cargo_id.state', 'in', state)])
        #orders = self.env['sale.order'].search([('shipment_id', '=', docs.shipment_id.id)])

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'data':cargos,
        }
        return self.env['report'].render('kalkaal_logistics.cargo_report', docargs)
class CargoWizard(models.TransientModel):
    _name = "logistics.cargo_wizard"
    _description = "cargo collection wizard"

    shipment_id = fields.Many2one('logistics.shipment',
        string="Select Shipment")

    state = fields.Selection([
        ('collected', 'Collected'),
        ('billed', 'Service Ordered'),
        ])

    customer_id = fields.Many2one('res.partner',string="Customer")

    #date_from = fields.Datetime(string='Start Date')
    #date_to = fields.Datetime(string='End Date')
    @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['shipment_id','state','customer_id'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['shipment_id','state','customer_id'])[0])
        return self.env['report'].get_action(self, 'kalkaal_logistics.cargo_report', data=data)
