import React, { Component } from 'react';
import { View } from 'react-native';
import moment from 'moment';
import styles from './styles';
import InvoiceList from '../../qubiqle/InvoiceList';
import FilterBar from '../../qubiqle/FilterBar';
import SearchBar from '../../qubiqle/SearchBar';
import InvoiceFilter from '../../qubiqle/Filter';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import NoAccessView from '../../qubiqle/NoAccessView';

export default class AllInvoices extends Component {
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
            sendMixpanelEvent(MixpanelEvents.INVOICES_SEARCHED);
          }}
          placeholder="Search Invoices"
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

    if (!isSearchVisible) {
      return (
        <FilterBar
          title="Select Time Range"
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
      <InvoiceFilter
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
      invoices, loading, loadNextPage, firstLoad, goToInvoiceDetail, isSearchVisible, canAccessDashboard
    } = this.props;

    if (!canAccessDashboard) return <NoAccessView />;

    return (
      <View>
        {this.renderSearch()}
        {this.renderFilterBar()}
        {this.renderFilter()}

        <InvoiceList
          style={styles.invoiceList}
          firstLoad={firstLoad}
          invoices={invoices}
          loadNextPage={loadNextPage}
          loading={loading}
          onPress={goToInvoiceDetail}
          emptyMessage={isSearchVisible ? 'No Matching Results' : null}
        />
      </View>
    );
  }
}
