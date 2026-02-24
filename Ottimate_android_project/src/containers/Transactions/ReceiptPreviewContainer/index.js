import React, { Component } from 'react';
import { connect } from 'react-redux';
import { deleteFile } from '../../../utils/FileUtil';
import ReceiptPreview from '../../../components/Transactions/ReceiptPreview';
import { addTransactionPendingUpload, mapTransactionReceipt, refreshTransaction } from '../../../actions';
import { showErrorToast } from '../../../utils/Toaster';

class ReceiptPreviewContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
    };
  }

  discard = async () => {
    const { image } = this.props.navigation.state.params;
    try {
      await deleteFile(image);
    } catch (e) {

    }
    this.props.navigation.goBack();
  };

  upload = async () => {
    const {
      transaction, image, refreshTransactions, unassigned
    } = this.props.navigation.state.params;
    if (unassigned) {
      this.uploadUnassigned();
      return;
    }
    const { card, id } = transaction;
    const { company } = card;
    const { remote_id } = company;
    this.props.addTransactionPendingUpload(id, remote_id, image);
    if (refreshTransactions) {
      refreshTransactions(1);
    }
    this.props.navigation.goBack();
  };

  uploadUnassigned = async () => {
    const {
      transaction, image, refreshTransactions, refreshUnassignedReceipts
    } = this.props.navigation.state.params;
    const { card, id } = transaction;
    const { company } = card;
    const { remote_id } = company;

    await this.setState({ isLoading: true });
    const res = await mapTransactionReceipt(id, remote_id, image);
    await this.setState({ isLoading: false });
    if (res) {
      if (refreshTransactions) {
        refreshTransactions(1);
      }
      if (refreshUnassignedReceipts) {
        refreshUnassignedReceipts();
        this.props.refreshTransaction(id, remote_id);
      }
      this.props.navigation.goBack();
    } else {
      showErrorToast('Transactions mapping failed');
    }
  };

  render() {
    const { transaction, image } = this.props.navigation.state.params;
    const { isLoading } = this.state;

    return (
      <ReceiptPreview
        transaction={transaction}
        image={image}
        discard={this.discard}
        upload={this.upload}
        isLoading={isLoading}
      />
    );
  }
}

const mapStateToProps = () => ({
});

export default connect(
  mapStateToProps, { addTransactionPendingUpload, refreshTransaction }
)(ReceiptPreviewContainer);
