import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadAllTransactions, resetAllTransactions, setCurrentTransaction, updateReceiptProgress
} from '../../../actions';
import Adapter from '../../../utils/Adapter';
import AllTransactions from '../../../components/Transactions/AllTransactions';

class AllTransactionContainer extends Component {
  static navigationOptions = () => ({
    title: 'Transactions'
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

  // eslint-disable-next-line react/sort-comp
  listener= (receipts, changes) => {
    // Update UI in response to modified objects
    changes.modifications.forEach((receiptIndex) => {
      const receipt = receipts[receiptIndex];
      const { data } = this.props.transactions;
      const index = data.findIndex((current) => current.id === receipt.transactionId);
      if (receipt) this.props.updateReceiptProgress({ receipt, index });
    });
  }

  setFilter = async (filters) => {
    await this.setState({ filters });
    await this.props.resetAllTransactions();
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

    const filter = { page, ordering: '-posting_date,-created_date' };

    if (searchText) filter.query = searchText;
    if (company) filter.company = company.id;

    if ((next || page === 1) && !loading) {
      this.props.loadAllTransactions(filter);
    }
  };

  goToTransactionDetail = (index) => {
    this.props.setCurrentTransaction(null);
    this.props.navigation.navigate('TransactionDetail', {
      type: 'all',
      index
    });
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

  render() {
    const { loading, data, firstLoad } = this.props.transactions;
    const { resetAllTransactions } = this.props;
    const {
      searchText, isSearchVisible, isFilterVisible, filters
    } = this.state;
    return (
      <AllTransactions
        firstLoad={firstLoad}
        loading={loading}
        transactions={data}
        loadNextPage={this.loadNextPage}
        goToTransactionDetail={this.goToTransactionDetail}
        onSearchClick={resetAllTransactions}
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
  transactions: state.allTransactions,
});

export default connect(
  mapStateToProps,
  {
    loadAllTransactions, resetAllTransactions, setCurrentTransaction, updateReceiptProgress
  }
)(AllTransactionContainer);
