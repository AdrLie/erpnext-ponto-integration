frappe.ui.form.on('Ponto Settings', {
    refresh: (frm) => {
        frm.add_custom_button(__('Fetch Token Now'), () => {
            frm.call({
                doc: frm.doc,
                method: 'fetch_new_token',
                freeze: true,
                freeze_message: __('Connecting to Ponto API...'),
                callback: (r) => {
                    if (!r.exc) {
                        frm.reload_doc();
                    }
                }
            });
        }).addClass('btn-primary');
    }
});