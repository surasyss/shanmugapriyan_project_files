import React, { Component } from 'react';
import { connect } from 'react-redux';
import { addPendingUpload } from '../../../actions';
import InvoicePreview from '../../../components/Upload/InvoicePreview';
import { deleteFile } from '../../../utils/FileUtil';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';

class InvoicePreviewContainer extends Component {
  discard = async () => {
    const { image } = this.props.navigation.state.params;
    await deleteFile(image);
    this.props.navigation.goBack();
  };

  upload = () => {
    sendMixpanelEvent(MixpanelEvents.INVOICE_UPLOADED);
    const { restaurant, image } = this.props.navigation.state.params;
    this.props.addPendingUpload(restaurant, image, null, {});
    this.props.navigation.goBack();
  };

  render() {
    const { restaurant, image } = this.props.navigation.state.params;

    return (
      <InvoicePreview
        restaurant={restaurant}
        image={image}
        discard={this.discard}
        upload={this.upload}
      />
    );
  }
}

const mapStateToProps = () => ({
});

export default connect(
  mapStateToProps,
  { addPendingUpload }
)(InvoicePreviewContainer);
