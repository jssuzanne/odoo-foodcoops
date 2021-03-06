# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class ShiftShift(models.Model):
    _inherit = "shift.shift"

    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'), ('entry', 'Entry'), ('done', 'Done')])

    standard_registration_ids = fields.One2many(
        "shift.registration",
        "shift_id",
        string="Standard Attendances",
        domain=[('shift_type', '=', 'standard')])

    ftop_registration_ids = fields.One2many(
        "shift.registration",
        "shift_id",
        string="FTOP Attendances",
        domain=[('shift_type', '=', 'ftop')])

    @api.multi
    def button_makeupok(self):
        '''
        @Function trigger to change the state from Confirm to Entry
        '''
        for shift in self:
            shift.state = 'entry'
            # When members are added to the list of attendees via the make-up
            # "rattrapages" page, they should be automatically marked present
            # when we come to the page for marking the attendance.
            # Members entered for doing make-up are always present.
            # These members are determined by:
            # - They don't replace for anyone.
            # - They are not registered for this shift's template before
            for reg in shift.standard_registration_ids:
                if reg.state == 'replacing' or reg.tmpl_reg_line_id:
                    continue
                reg.button_reg_close()
            for reg in shift.ftop_registration_ids:
                if reg.state == 'replacing' or reg.tmpl_reg_line_id:
                    continue
                reg.button_reg_close()

    @api.multi
    def button_done(self):
        '''
        @Overide the function to validate the registration before allowing
        marking the shift done
        '''
        for shift in self:
            if not shift.shift_type_id.is_ftop:
                not_recorded_attendances = shift.registration_ids.filtered(
                    lambda x: x.state in ['draft', 'open'])
                if not_recorded_attendances:
                    shift_ticket_partners = []
                    for att in not_recorded_attendances:
                        ticket_name = att.shift_ticket_id.name or ''
                        partner_name = att.partner_id.name or ''
                        shift_ticket_partners.append(
                            "- [%s] %s" % (ticket_name, partner_name))
                    raise UserError(_(
                        "Warning! You have not recorded the attendance " +
                        "for: \n\n%s") % '\n'.join(shift_ticket_partners))

        return super(ShiftShift, self).button_done()

    @api.multi
    def write(self, vals):
        res = super(ShiftShift, self).write(vals)
        # change to unconfirmed registrations to confirmed if this shift state
        # is `entry`
        for shift in self:
            if shift.state == 'entry':
                for reg in shift.standard_registration_ids:
                    if reg.state == 'draft':
                        reg.confirm_registration()
                for reg in shift.ftop_registration_ids:
                    if reg.state == 'draft':
                        reg.confirm_registration()
        return res