import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadAllPurchasedItems, resetAllPurchasedItems, setCurrentPurchasedItem, loadPurchasedItemDetails, markStar,
  loadStarredPurchasedItems, markStarLocal, deleteStar
} from '../../../actions';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import AllPurchasedItems from '../../../components/PurchasedItems/AllPurchasedItems';
import { getDateRange } from '../../../utils/DateFormatter';
import showAlert from '../../../utils/QubiqleAlert';

class AllPurchasedItemsContainer extends Component {
  static navigationOptions = () => ({
    title: 'Items'
  });

  constructor(props) {
    super(props);
    this.state = {
      isLoading: false,
      searchText: '',
      isSearchVisible: false,
      isFilterVisible: false,
      filters: {
        date_type: { key: 'last_3_months', name: 'Last 3 Months' },
        date_range: getDateRange('last_3_months')
      }
    };
  }

  async componentDidMount() {
    this.loadNextPage(1);
  }

  async setFilter(filters) {
    await this.setState({ filters });
    await this.props.resetAllPurchasedItems();
    this.loadNextPage(1);
    sendMixpanelEvent(MixpanelEvents.ITEMS_TAB_OPENED, { filters });
  }

  goToPurchasedItemDetail = (index) => {
    const { filters } = this.state;
    const { date_range } = filters;
    let start_date = null;
    let end_date = null;
    if (date_range) {
      const { start, end } = date_range;
      start_date = start;
      end_date = end;
    }

    const item = this.props.purchasedItems.data[index];
    sendMixpanelEvent(MixpanelEvents.ITEMS_OPENED, { item });
    this.props.setCurrentPurchasedItem(null);
    this.props.loadPurchasedItemDetails(item.id, start_date, end_date);
    this.props.navigation.navigate('PurchasedItemDetail', {
      type: 'all',
      index,
      start_date,
      end_date
    });
  };

  starItem = async (index) => {
    const { data } = this.props.purchasedItems;
    const item = data[index];
    const starred = !item.starred;

    await this.setState({ isLoading: true });
    let errorMessage = null;
    if (starred) {
      errorMessage = await markStar(item);
    } else {
      errorMessage = await deleteStar(item);
    }

    await this.setState({ isLoading: false });
    if (errorMessage) {
      showAlert('Error', errorMessage);
      return;
    }
    this.props.markStarLocal(item, starred);
    this.props.loadStarredPurchasedItems({});
  };

  loadNextPage(nextPage) {
    const { searchText, filters } = this.state;

    let { page } = this.props.purchasedItems;
    const { next, loading } = this.props.purchasedItems;
    page += 1;
    const {
      vendor, date_range
    } = filters;

    if (nextPage) page = nextPage;

    const filter = { page };

    if (searchText) filter.query = searchText;
    if (vendor) filter.vendor_id = vendor.id;
    if (date_range) {
      const { start, end } = date_range;
      filter.start_date = start;
      filter.end_date = end;
    }

    if ((next || page === 1) && !loading) {
      this.props.loadAllPurchasedItems(filter);
    }
  }

  openSearch(isSearchVisible) {
    this.setState({ isSearchVisible });
  }

  changeSearchQuery(searchText) {
    this.setState({ searchText });
  }

  openFilter(isFilterVisible) {
    this.setState({ isFilterVisible });
  }

  render() {
    const { loading, data, firstLoad } = this.props.purchasedItems;
    const { canAccessDashboard } = this.props.userInfo;
    const loadNextPage = this.loadNextPage.bind(this);
    const { resetAllPurchasedItems } = this.props;
    const { searchText, isSearchVisible, isFilterVisible } = this.state;
    const openSearch = this.openSearch.bind(this);
    const changeSearchQuery = this.changeSearchQuery.bind(this);
    const openFilter = this.openFilter.bind(this);
    const setFilter = this.setFilter.bind(this);
    const { filters, isLoading } = this.state;

    return (
      <AllPurchasedItems
        isLoading={isLoading}
        firstLoad={firstLoad}
        loading={loading}
        items={data}
        loadNextPage={loadNextPage}
        onSearchClick={resetAllPurchasedItems}
        searchText={searchText}
        isSearchVisible={isSearchVisible}
        openSearch={openSearch}
        changeSearchQuery={changeSearchQuery}
        isFilterVisible={isFilterVisible}
        openFilter={openFilter}
        setFilter={setFilter}
        filters={filters}
        onPress={this.goToPurchasedItemDetail}
        starItem={this.starItem}
        canAccessDashboard={canAccessDashboard}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  purchasedItems: state.allPurchasedItems,
  userInfo: state.userInfo,
});

export default connect(
  mapStateToProps,
  {
    loadAllPurchasedItems, resetAllPurchasedItems, setCurrentPurchasedItem, loadPurchasedItemDetails, markStarLocal, loadStarredPurchasedItems
  }
)(AllPurchasedItemsContainer);
