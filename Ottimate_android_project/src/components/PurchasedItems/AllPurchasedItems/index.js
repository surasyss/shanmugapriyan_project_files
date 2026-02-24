import React, { Component } from 'react';
import { Platform, View } from 'react-native';
import moment from 'moment';
import styles from './styles';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import SearchBar from '../../qubiqle/SearchBar';
import PurchasedItemsList from '../PurchasedItemsList';
import PurchasedItemsFilter from '../PurchasedItemsFilter';
import PurchasedItemsFilterBar from '../PurchasedItemsFilterBar';
import Spinner from '../../qubiqle/Spinner';
import Colors from '../../../styles/Colors';
import NoAccessView from '../../qubiqle/NoAccessView';

export default class AllPurchasedItems extends Component {
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
            sendMixpanelEvent(MixpanelEvents.ITEMS_SEARCHED);
          }}
          placeholder="Search items, SKUs, Vendors.."
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
      let title = '';
      const { date_type } = filters;
      if (date_type) {
        const { name } = date_type;
        if (name) {
          title = name;
        }
      }
      return (
        <PurchasedItemsFilterBar
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
      <PurchasedItemsFilter
        key={new moment().toString()}
        isVisible={isFilterVisible}
        openFilter={openFilter}
        setFilter={setFilter}
        filters={filters}
      />
    );
  }

  renderLoadingDialog() {
    const { isLoading } = this.props;
    return (
      <Spinner
        visible={isLoading}
        color={Platform.OS === 'ios' ? Colors.white : Colors.primary}
      />
    );
  }

  render() {
    const {
      items, loading, loadNextPage, firstLoad, onPress, starItem, canAccessDashboard
    } = this.props;

    if (!canAccessDashboard) return <NoAccessView />;

    return (
      <View>
        {this.renderSearch()}
        {this.renderFilter()}
        {this.renderFilterBar()}
        {this.renderLoadingDialog()}
        <PurchasedItemsList
          style={styles.itemsList}
          firstLoad={firstLoad}
          items={items}
          loadNextPage={loadNextPage}
          loading={loading}
          emptyMessage={loading ? 'Loading Items' : 'No Matching Results'}
          onPress={onPress}
          starItem={starItem}
        />
      </View>
    );
  }
}
