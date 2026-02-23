import React, { Component } from 'react';
import { connect } from 'react-redux';
import moment from 'moment';
import {
  setAddCreditRequestData, createCreditRequest
} from '../../../actions';
import AddCreditRequestComponent from '../../../components/CreditRequests/AddCreditRequestComponent';
import Adapter from '../../../utils/Adapter';

class AddCreditRequestContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      user: {}
    };
  }

  async componentDidMount() {
    const user = await Adapter.getUser();
    this.setState({ user });
  }

  submit = () => {
    const { user } = this.state;
    const { addCreditRequest, createCreditRequest } = this.props;
    const { data } = addCreditRequest;
    const {
      vendor, restaurant, invoice_number, invoice_date, total_amount, notes
    } = data;
    if (vendor && restaurant && invoice_number && invoice_date && total_amount && notes) {
      const data = {
        vendor: vendor.id,
        restaurant: restaurant.id,
        invoice_number,
        date: new moment(invoice_date, 'MM/DD/YYYY').format('YYYY-MM-DD'),
        total_amount,
        upload_id: `new_invoice${moment()}${user.id}`,
        upload_through: 'directly created',
        invoice_type: 'credit request',
        notes
      };
      createCreditRequest(data);
    }
  };

  goToRestaurantPicker = () => {
    const { setAddCreditRequestData } = this.props;
    this.props.navigation.navigate('RestaurantPicker', {
      onSelect: (restaurant) => {
        setAddCreditRequestData('restaurant', restaurant);
      }
    });
  };

  goToVendorPicker = () => {
    const { setAddCreditRequestData } = this.props;
    this.props.navigation.navigate('VendorPicker', {
      onSelect: (vendor) => {
        setAddCreditRequestData('vendor', vendor);
      }
    });
  };

  render() {
    const { setAddCreditRequestData, addCreditRequest } = this.props;
    const { data, loading } = addCreditRequest;

    return (
      <AddCreditRequestComponent
        setData={setAddCreditRequestData}
        goToRestaurantPicker={this.goToRestaurantPicker}
        goToVendorPicker={this.goToVendorPicker}
        data={data}
        submit={this.submit}
        loading={loading}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  addCreditRequest: state.addCreditRequest
});

export default connect(
  mapStateToProps,
  {
    setAddCreditRequestData, createCreditRequest
  }
)(AddCreditRequestContainer);
