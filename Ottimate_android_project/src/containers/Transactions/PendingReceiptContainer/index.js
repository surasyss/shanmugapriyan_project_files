import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadPendingReceiptTransactions, resetPendingReceiptTransactions, setCurrentTransaction, updatePendingReceiptProgress
} from '../../../actions';
import PendingReceipts from '../../../components/Transactions/PendingReceipts';
import Adapter from '../../../utils/Adapter';

class PendingReceiptContainer extends Component {
  static navigationOptions = () => ({
    title: 'Select Transaction',
  });

  constructor(props) {
    super(props);
    this.state = {
      searchText: '',
      isSearchVisible: false,
      isFilterVisible: false,
      filters: {}
    };
  }

  async componentDidMount() {
    const currentCompany = await Adapter.getCurrentCompany();
    this.selectCompany(currentCompany);
    this.loadNextPage(1);
  }

  setFilter = async (filters) => {
    await this.setState({ filters });
    await this.props.resetPendingReceiptTransactions();
    this.loadNextPage(1);
    await Adapter.setCurrentCompany(this.state.filters.company);
  };

  loadNextPage = (nextPage) => {
    const { searchText, filters } = this.state;

    let { page } = this.props.transactions;
    const { next, loading } = this.props.transactions;
    page += 1;
    const {
      company
    } = filters;

    if (nextPage) page = nextPage;

    const filter = { page };

    if (searchText) filter.query = searchText;
    if (company) filter.company = company.id;

    if ((next || page === 1) && !loading) {
      this.props.loadPendingReceiptTransactions(filter);
    }
  };

  goToTransactionDetail = (index) => {
    const { data } = this.props.transactions;
    const transaction = data[index];
    this.props.navigation.navigate('ReceiptCamera', { transaction, refreshTransactions: this.loadNextPage });
  };

  openSearch = (isSearchVisible) => {
    this.setState({ isSearchVisible });
  };

  changeSearchQuery = (searchText) => {
    this.setState({ searchText });
  };

  openFilter = (isFilterVisible) => {
    this.setState({ isFilterVisible });
  };

  selectCompany = (company) => {
    const { filters } = this.state;
    filters.company = company;
    this.setState({
      filters
    });
  };

  listener= (receipts, changes) => {
    // Update UI in response to modified objects
    changes.modifications.forEach((receiptIndex) => {
      const receipt = receipts[receiptIndex];
      const { data } = this.props.transactions;
      const index = data.findIndex((current) => current.id === receipt.transactionId);
      if (receipt) this.props.updatePendingReceiptProgress({ receipt, index });
    });
  }

  render() {
    const { loading, data, firstLoad } = this.props.transactions;
    const { resetPendingReceiptTransactions } = this.props;
    const {
      searchText, isSearchVisible, isFilterVisible, filters
    } = this.state;

    return (
      <PendingReceipts
        firstLoad={firstLoad}
        loading={loading}
        transactions={data}
        loadNextPage={this.loadNextPage}
        goToTransactionDetail={this.goToTransactionDetail}
        onSearchClick={resetPendingReceiptTransactions}
        searchText={searchText}
        isSearchVisible={isSearchVisible}
        openSearch={this.openSearch}
        changeSearchQuery={this.changeSearchQuery}
        isFilterVisible={isFilterVisible}
        openFilter={this.openFilter}
        setFilter={this.setFilter}
        filters={filters}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  transactions: state.pendingReceiptTransactions,
  currentCompany: state.userInfo.currentCompany,
});

export default connect(
  mapStateToProps,
  {
    loadPendingReceiptTransactions, resetPendingReceiptTransactions, setCurrentTransaction, updatePendingReceiptProgress
  }
)(PendingReceiptContainer);
