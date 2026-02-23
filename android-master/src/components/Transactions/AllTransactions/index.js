import React, { Component } from 'react';
import { View } from 'react-native';
import moment from 'moment';
import styles from './styles';
import FilterBar from '../../qubiqle/FilterBar';
import SearchBar from '../../qubiqle/SearchBar';
import TransactionList from '../TransactionList';
import TransactionFilter from '../TransactionFilter';

export default class AllTransactions extends Component {
  renderSearch() {
    const {
      loadNextPage, searchText, isSearchVisible, openSearch, changeSearchQuery
    } = this.props;

    if (isSearchVisible) {
      return (
        <SearchBar
          onSearchCancel={async () => {
            await openSearch(false);
            await changeSearchQuery('');
            loadNextPage(1);
          }}
          onTextChange={(text) => {
            changeSearchQuery(text);
          }}
          searchText={searchText}
          onSubmit={() => {
            loadNextPage(1);
          }}
          placeholder="Search Transaction"
        />
      );
    }

    return (
      <View />
    );
  }

  renderFilterBar() {
    const {
      onSearchClick, isSearchVisible, openSearch, openFilter, filters
    } = this.props;
    const { company } = filters;
    let title = 'Select Company';
    if (company) {
      title = company.name;
    }

    if (!isSearchVisible) {
      return (
        <FilterBar
          title={title}
          onSearch={() => {
            openSearch(true);
            onSearchClick();
          }}
          onFilter={() => openFilter(true)}
          filters={filters}
        />
      );
    }
    return (
      <View />
    );
  }

  renderFilter() {
    const {
      isFilterVisible, openFilter, setFilter, filters
    } = this.props;
    return (
      <TransactionFilter
        key={new moment().toString()}
        isVisible={isFilterVisible}
        openFilter={openFilter}
        setFilter={setFilter}
        filters={filters}
      />
    );
  }

  render() {
    const {
      transactions, loading, loadNextPage, firstLoad, isSearchVisible, goToTransactionDetail, filters
    } = this.props;
    let emptyMessage = 'Apply filters to filter Transactions';
    if (isSearchVisible) {
      emptyMessage = 'No Matching Results';
    }
    if (!filters.company) {
      emptyMessage = 'Select a company';
    }

    return (
      <View>
        {this.renderSearch()}
        {this.renderFilterBar()}
        {this.renderFilter()}
        <TransactionList
          style={styles.transactionList}
          onPress={goToTransactionDetail}
          firstLoad={firstLoad}
          transactions={transactions}
          loadNextPage={loadNextPage}
          loading={loading}
          emptyMessage={emptyMessage}
        />
      </View>
    );
  }
}
