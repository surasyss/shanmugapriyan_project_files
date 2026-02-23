import React, { Component } from 'react';
import { connect } from 'react-redux';
import Adapter from '../../../utils/Adapter';
import UploadInvoice from '../../../components/Upload/UploadInvoice';
import {
  loadPendingUploads, handlePendingUpload, loadTransactionPendingUploads, handlePendingTransactionUpload
} from '../../../actions';

class UploadInvoiceContainer extends Component {
  static navigationOptions = () => ({
    title: 'Upload'
  });

  constructor(props) {
    super(props);
    this.state = {
      restaurants: []
    };
  }

  async componentDidMount() {
    this.refreshRestaurants();
    await this.props.loadPendingUploads();
    await this.props.loadTransactionPendingUploads();
    const { data } = this.props.pendingUploads;
    data.forEach((invoice) => {
      this.props.handlePendingUpload(invoice);
    });
    this.props.pendingTransactionReceipts.data.forEach((transaction) => {
      this.props.handlePendingTransactionUpload(transaction);
    });
  }

  refreshRestaurants = async () => {
    const restaurants = await Adapter.getRestaurants();
    this.setState({ restaurants });
  };

  selectRestaurant = (restaurant) => {
    if (restaurant) {
      this.props.navigation.navigate('InvoiceCamera', { restaurant });
    }
  };

  onInvoiceDelete = async (invoice) => {
    this.props.navigation.navigate('DeleteInvoice', { invoice });
  };

  onReceiptUpload = () => {
    this.props.navigation.navigate('PendingReceipts');
  }

  render() {
    const { restaurants } = this.state;
    const { data } = this.props.pendingUploads;
    const { canUploadInvoice, showTransactions } = this.props;

    return (
      <UploadInvoice
        restaurants={restaurants}
        selectRestaurant={this.selectRestaurant}
        refreshRestaurants={this.refreshRestaurants}
        onInvoiceDelete={this.onInvoiceDelete}
        onReceiptUpload={this.onReceiptUpload}
        canUploadInvoice={canUploadInvoice}
        showTransactions={showTransactions}
        data={data}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  pendingUploads: state.pendingUploads,
  pendingTransactionReceipts: state.pendingTransactionReceipts,
  canUploadInvoice: state.userInfo.canUploadInvoice,
  showTransactions: state.userInfo.showTransactions,
});

export default connect(
  mapStateToProps,
  {
    loadPendingUploads, handlePendingUpload, loadTransactionPendingUploads, handlePendingTransactionUpload
  }
)(UploadInvoiceContainer);
