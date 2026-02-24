import React from 'react';
import {
  View, Text, TouchableOpacity, TouchableHighlight, Image
} from 'react-native';
import Modal from 'react-native-modal';
import ModalDropdown from 'react-native-modal-dropdown';
import { connect } from 'react-redux';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import styles from './styles';
import Colors from '../../../styles/Colors';
import Adapter from '../../../utils/Adapter';
import Button from '../../qubiqle/Button';
import Images from '../../../styles/Images';

class TransactionFilter extends React.Component {
  constructor(props) {
    super(props);
    const {
      company
    } = props.filters;

    this.state = {
      company,
      companies: [],
    };
  }

  async componentDidMount() {
    const companies = await Adapter.getCompanies();
    this.setState({ companies });
  }

  apply() {
    const {
      company
    } = this.state;
    const { setFilter, openFilter } = this.props;
    const filters = {
      company
    };
    setFilter(filters);
    openFilter(false);
  }

  clear() {
    this.setState({
    });
  }

  renderDropDownRow(rowData) {
    return (
      <TouchableHighlight underlayColor={Colors.dividerColor}>
        <View style={styles.dropDownRow}>
          <Text style={styles.dropDownRowText}>
            {rowData.name}
          </Text>
        </View>
      </TouchableHighlight>
    );
  }

  renderDropDownDivider() {
    return (
      <View style={styles.dropDownDivider} />);
  }

  renderForm() {
    const {
      company, companies
    } = this.state;

    return (
      <View style={styles.formContainer}>
        <Text style={styles.formHeading}>COMPANY</Text>
        <ModalDropdown
          ref="company_dropdown"
          style={styles.dropDown}
          defaultValue="Select"
          dropdownStyle={styles.dropDownList}
          options={companies}
          renderRow={this.renderDropDownRow.bind(this)}
          renderSeparator={this.renderDropDownDivider.bind(this)}
          onSelect={(idx, value) => {
            this.setState({ company: value });
          }}
        >
          <View style={styles.dropDownButton}>
            <Text style={company ? styles.dropDownText : styles.dropDownPlaceholder}>{company ? company.name : 'Select'}</Text>
            <Image
              resizeMode="contain"
              source={Images.filter_down}
              style={styles.filterRightIcon}
            />
          </View>
        </ModalDropdown>
        <Button
          type="primary"
          title="Apply Filters"
          style={styles.applyButton}
          onPress={() => this.apply()}
        />
      </View>
    );
  }

  render() {
    const { isVisible, openFilter } = this.props;

    return (
      <Modal
        hideModalContentWhileAnimating
        animationIn="slideInUp"
        animationOut="slideOutDown"
        style={styles.container}
        transparent
        isVisible={isVisible}
        backdropOpacity={0.5}
        onRequestClose={() => openFilter(false)}
      >

        <KeyboardAwareScrollView
          style={styles.scrollContainer}
          keyboardShouldPersistTaps="always"
          scrollEnabled={this.state.enableScrollViewScroll}
        >
          <View style={styles.header}>
            <TouchableOpacity style={styles.flex_1} onPress={() => openFilter(false)}>
              <Text style={styles.headerCancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <View style={styles.flex_1}>
              <Text style={styles.headerTitle}>Filters</Text>
            </View>
            <TouchableOpacity style={styles.flex_1} onPress={() => this.clear()}>
              <Text style={styles.headerClearButtonText}>Clear</Text>
            </TouchableOpacity>
          </View>
          {this.renderForm()}
        </KeyboardAwareScrollView>
      </Modal>
    );
  }
}

const mapStateToProps = () => ({
});

export default connect(
  mapStateToProps,
  { }
)(TransactionFilter);
