import React, { Component } from 'react';
import { View } from 'react-native';
import moment from 'moment';
import styles from './styles';
import SearchBar from '../../qubiqle/SearchBar';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import CreditRequestFilterBar from '../CreditRequestFilterBar';
import CreditRequestFilter from '../CreditRequestFilter';
import CreditRequestList from '../CreditRequestList';

export default class AllCreditRequests extends Component {
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
            sendMixpanelEvent(MixpanelEvents.CREDIT_REQUESTS_SEARCHED);
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
        <CreditRequestFilterBar
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
      <CreditRequestFilter
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
      creditRequests, loading, loadNextPage, firstLoad, goToCreditRequestDetail, isSearchVisible
    } = this.props;

    return (
      <View>
        {this.renderSearch()}
        {this.renderFilterBar()}
        {this.renderFilter()}

        <CreditRequestList
          style={styles.invoiceList}
          firstLoad={firstLoad}
          creditRequests={creditRequests}
          loadNextPage={loadNextPage}
          loading={loading}
          onPress={goToCreditRequestDetail}
          emptyMessage={isSearchVisible ? 'No Matching Results' : null}
        />
      </View>
    );
  }
}
