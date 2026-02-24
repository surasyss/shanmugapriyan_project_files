import React, { Component } from 'react';
import { connect } from 'react-redux';
import { deletePendingUpload } from '../../../actions';
import { deleteFile } from '../../../utils/FileUtil';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import DeleteInvoice from '../../../components/Upload/DeleteInvoice';
import PendingUploadAdapter from '../../../utils/PendingUploadAdapter';

class DeleteInvoiceContainer extends Component {
  close = () => {
    this.props.navigation.goBack();
  };

  deleteImage = async () => {
    sendMixpanelEvent(MixpanelEvents.INVOICE_DELETED);
    const { invoice } = this.props.navigation.state.params;
    await deleteFile(invoice.image);
    await PendingUploadAdapter.deleteInvoice(invoice);
    await this.props.deletePendingUpload(invoice);
    this.props.navigation.goBack();
  };

  render() {
    const { invoice } = this.props.navigation.state.params;

    return (
      <DeleteInvoice
        invoice={invoice}
        close={this.close}
        deleteImage={this.deleteImage}
      />
    );
  }
}

const mapStateToProps = () => ({
});

export default connect(
  mapStateToProps,
  { deletePendingUpload }
)(DeleteInvoiceContainer);
