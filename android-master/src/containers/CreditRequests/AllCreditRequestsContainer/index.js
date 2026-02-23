import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadRestaurantUsers, loadAllCreditRequests, resetAllCreditRequests, loadCreditRequestDetails, setCurrentCreditRequest
} from '../../../actions';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import AllCreditRequests from '../../../components/CreditRequests/AllCreditRequests';

class AllCreditRequestsContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      searchText: '',
      isSearchVisible: false,
      isFilterVisible: false,
      filters: {}
    };
  }

  componentDidMount() {
    this.props.loadAllCreditRequests({});
  }

  async setFilter(filters) {
    await this.setState({ filters });
    await this.props.resetAllCreditRequests();
    this.loadNextPage(1);
    sendMixpanelEvent(MixpanelEvents.CREDIT_REQUESTS_FILTERED, { filters });
  }

  loadNextPage(nextPage) {
    const { searchText, filters } = this.state;

    let { page } = this.props.allCreditRequests;
    const { next, loading } = this.props.allCreditRequests;
    page += 1;

    const {
      restaurant, vendor, company, date_range, date_type
    } = filters;

    if (nextPage) page = nextPage;

    const filter = { page };

    if (searchText) filter.query = searchText;
    if (restaurant) filter.restaurant = restaurant.id;
    if (vendor) filter.vendor = vendor.id;
    if (company) filter.company = company.id;
    if (date_range) {
      let type = 'date';
      if (date_type) type = date_type.key;
      const { start, end } = date_range;
      filter[`${type}__gte`] = start;
      filter[`${type}__lte`] = end;
    }

    if ((next || page === 1) && !loading) {
      this.props.loadAllCreditRequests(filter);
    }
  }

  goToCreditRequestDetail(index) {
    const creditRequest = this.props.allCreditRequests.data[index];
    sendMixpanelEvent(MixpanelEvents.CREDIT_REQUEST_OPENED, { credit_request: creditRequest });
    this.props.setCurrentCreditRequest(null);
    this.props.loadCreditRequestDetails(creditRequest.id);
    this.props.loadRestaurantUsers(creditRequest.restaurant);
    this.props.navigation.navigate('CreditRequestDetail', {
      type: 'all',
      index
    });
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
    const { loading, data, firstLoad } = this.props.allCreditRequests;
    const loadNextPage = this.loadNextPage.bind(this);
    const goToCreditRequestDetail = this.goToCreditRequestDetail.bind(this);
    const { resetAllCreditRequests } = this.props;
    const { searchText, isSearchVisible, isFilterVisible } = this.state;
    const openSearch = this.openSearch.bind(this);
    const changeSearchQuery = this.changeSearchQuery.bind(this);
    const openFilter = this.openFilter.bind(this);
    const setFilter = this.setFilter.bind(this);
    const { filters } = this.state;

    return (
      <AllCreditRequests
        firstLoad={firstLoad}
        loading={loading}
        creditRequests={data}
        loadNextPage={loadNextPage}
        goToCreditRequestDetail={goToCreditRequestDetail}
        onSearchClick={resetAllCreditRequests}
        searchText={searchText}
        isSearchVisible={isSearchVisible}
        openSearch={openSearch}
        changeSearchQuery={changeSearchQuery}
        isFilterVisible={isFilterVisible}
        openFilter={openFilter}
        setFilter={setFilter}
        filters={filters}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  allCreditRequests: state.allCreditRequests,
});

export default connect(
  mapStateToProps,
  {
    loadRestaurantUsers, loadAllCreditRequests, resetAllCreditRequests, loadCreditRequestDetails, setCurrentCreditRequest
  }
)(AllCreditRequestsContainer);
