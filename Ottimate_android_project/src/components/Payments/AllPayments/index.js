import React, { Component } from 'react';
import { View } from 'react-native';
import moment from 'moment';
import styles from './styles';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import FilterBar from '../../qubiqle/FilterBar';
import SearchBar from '../../qubiqle/SearchBar';
import PaymentList from '../../qubiqle/PaymentList';
import PaymentFilter from '../PaymentFilter';
import NoAccessView from '../../qubiqle/NoAccessView';

export default class AllPayments extends Component {
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
            sendMixpanelEvent(MixpanelEvents.PAYMENT_SEARCHED);
          }}
          placeholder="Search Payments"
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
      <PaymentFilter
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
      payments, loading, loadNextPage, firstLoad, isSearchVisible, goToPaymentDetail, canAccessDashboard
    } = this.props;

    if (!canAccessDashboard) return <NoAccessView />;

    return (
      <View>
        {this.renderSearch()}
        {this.renderFilterBar()}
        {this.renderFilter()}
        <PaymentList
          showStatus
          style={styles.paymentList}
          onPress={goToPaymentDetail}
          firstLoad={firstLoad}
          payments={payments}
          loadNextPage={loadNextPage}
          loading={loading}
          emptyMessage={isSearchVisible ? 'No Matching Results' : null}
        />
      </View>
    );
  }
}
