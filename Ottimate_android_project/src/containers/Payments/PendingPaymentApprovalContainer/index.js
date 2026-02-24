import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadPendingApprovalPayments, resetPendingApprovalPayments, setCurrentPayment
} from '../../../actions';
import PendingPaymentApproval from '../../../components/Payments/PendingPaymentApproval';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';

class PendingPaymentApprovalContainer extends Component {
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
    this.props.loadPendingApprovalPayments({});
  }

  async setFilter(filters) {
    await this.setState({ filters });
    await this.props.resetPendingApprovalPayments();
    this.loadNextPage(1);
    sendMixpanelEvent(MixpanelEvents.PAYMENT_FILTERED, { filters });
  }

  loadNextPage(nextPage) {
    const { searchText, filters } = this.state;

    let { page } = this.props.pendingPayments;
    const { next, loading } = this.props.pendingPayments;
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
      this.props.loadPendingApprovalPayments(filter);
    }
  }

  goToPaymentDetail(index) {
    const payment = this.props.pendingPayments.data[index];
    sendMixpanelEvent(MixpanelEvents.PAYMENT_OPENED, { payment });
    this.props.setCurrentPayment(null);
    // this.props.loadInvoiceDetails(invoice.id);
    this.props.navigation.navigate('PaymentDetail', {
      type: 'pending',
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
    const { loading, data, firstLoad } = this.props.pendingPayments;
    const { canAccessDashboard } = this.props.userInfo;
    const loadNextPage = this.loadNextPage.bind(this);
    const goToPaymentDetail = this.goToPaymentDetail.bind(this);
    // eslint-disable-next-line no-shadow
    const { resetPendingApprovalPayments } = this.props;
    const { searchText, isSearchVisible, isFilterVisible } = this.state;
    const openSearch = this.openSearch.bind(this);
    const changeSearchQuery = this.changeSearchQuery.bind(this);
    const openFilter = this.openFilter.bind(this);
    const setFilter = this.setFilter.bind(this);
    const { filters } = this.state;

    return (
      <PendingPaymentApproval
        firstLoad={firstLoad}
        loading={loading}
        payments={data}
        loadNextPage={loadNextPage}
        goToPaymentDetail={goToPaymentDetail}
        onSearchClick={resetPendingApprovalPayments}
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
  pendingPayments: state.pendingPayments,
  userInfo: state.userInfo,
});

export default connect(
  mapStateToProps,
  {
    loadPendingApprovalPayments, resetPendingApprovalPayments, setCurrentPayment
  }
)(PendingPaymentApprovalContainer);
