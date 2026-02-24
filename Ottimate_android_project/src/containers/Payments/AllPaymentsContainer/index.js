import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadAllPayments, resetAllPayments, setCurrentPayment
} from '../../../actions';
import AllPayments from '../../../components/Payments/AllPayments';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';

class AllPaymentsContainer extends Component {
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
    this.props.loadAllPayments({});
  }

  async setFilter(filters) {
    await this.setState({ filters });
    await this.props.resetAllPayments();
    this.loadNextPage(1);
    sendMixpanelEvent(MixpanelEvents.PAYMENT_FILTERED, { filters });
  }

  loadNextPage(nextPage) {
    const { searchText, filters } = this.state;

    let { page } = this.props.allPayments;
    const { next, loading } = this.props.allPayments;
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
      let type = 'scheduled_date';
      if (date_type) type = date_type.key;
      const { start, end } = date_range;
      filter[`${type}__gte`] = start;
      filter[`${type}__lte`] = end;
    }

    if ((next || page === 1) && !loading) {
      this.props.loadAllPayments(filter);
    }
  }

  goToPaymentDetail(index) {
    const payment = this.props.allPayments.data[index];
    sendMixpanelEvent(MixpanelEvents.PAYMENT_OPENED, { payment });
    this.props.setCurrentPayment(null);
    // this.props.loadInvoiceDetails(invoice.id);
    this.props.navigation.navigate('PaymentDetail', {
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
    const { loading, data, firstLoad } = this.props.allPayments;
    const { canAccessDashboard } = this.props.userInfo;
    const loadNextPage = this.loadNextPage.bind(this);
    const goToPaymentDetail = this.goToPaymentDetail.bind(this);
    // eslint-disable-next-line no-shadow
    const { resetAllPayments } = this.props;
    const { searchText, isSearchVisible, isFilterVisible } = this.state;
    const openSearch = this.openSearch.bind(this);
    const changeSearchQuery = this.changeSearchQuery.bind(this);
    const openFilter = this.openFilter.bind(this);
    const setFilter = this.setFilter.bind(this);
    const { filters } = this.state;

    return (
      <AllPayments
        firstLoad={firstLoad}
        loading={loading}
        payments={data}
        loadNextPage={loadNextPage}
        goToPaymentDetail={goToPaymentDetail}
        onSearchClick={resetAllPayments}
        searchText={searchText}
        isSearchVisible={isSearchVisible}
        openSearch={openSearch}
        changeSearchQuery={changeSearchQuery}
        isFilterVisible={isFilterVisible}
        openFilter={openFilter}
        setFilter={setFilter}
        filters={filters}
        canAccessDashboard={canAccessDashboard}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  allPayments: state.allPayments,
  userInfo: state.userInfo,
});

export default connect(
  mapStateToProps,
  {
    loadAllPayments, resetAllPayments, setCurrentPayment
  }
)(AllPaymentsContainer);
