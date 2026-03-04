frappe.ui.form.on('Bank Account', {
    refresh: (frm) => {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Sync Ponto Transactions'), () => {
                frappe.call({
                    method: 'ponto_integration.ponto_integration.api.sync_ponto_transactions',
                    args: {
                        bank_account: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Synchronizing transactions...'),
                    callback: (r) => {
                        if (!r.exc) {
                            frappe.show_alert({message: __('Sync Complete!'), indicator: 'green'});
                        }
                    }
                });
            }).addClass('btn-primary');
        }
    }
});