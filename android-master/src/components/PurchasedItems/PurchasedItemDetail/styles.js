import Colors from '../../../styles/Colors';

export default {
  scrollContainer: {
    backgroundColor: Colors.white
  },
  container: {
    flex: 1,
    backgroundColor: Colors.dividerColor
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderTopLeftRadius: 15,
    borderTopRightRadius: 15
  },
  tabSmall: {
    width: 50,
    alignItems: 'center',
    justifyContent: 'center',
    borderTopLeftRadius: 15,
    borderTopRightRadius: 15
  },
  tabs: {
    marginTop: 15,
    backgroundColor: 'rgb(236,241,247)',
    height: 45,
    flexDirection: 'row',
    borderTopWidth: 0,
    borderLeftWidth: 0,
    borderRightWidth: 0,
    borderTopLeftRadius: 15,
    borderTopRightRadius: 15
  },
  tabTextSelected: {
    width: '100%',
    textAlign: 'center',
    fontSize: 15,
    fontWeight: 'bold',
    color: 'rgb(0,0,0)',
  },
  tabTextUnSelected: {
    width: '100%',
    textAlign: 'center',
    fontSize: 15,
    fontWeight: '500',
    color: 'rgb(143,142,148)'
  },
  textEmpty: {
    color: Colors.secondaryText,
    paddingTop: 50,
    fontSize: 20,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'center'
  },
  header: {
    backgroundColor: Colors.white,
    paddingLeft: 20,
    paddingRight: 20
  },
  headerItem: {
    marginTop: 20,
    borderBottomColor: Colors.dividerColor,
    borderBottomWidth: 1
  },
  headerCategory: {
    marginTop: 20,
  },
  headerMultipleItems: {
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  headerHeading: {
    width: '100%',
    fontSize: 10,
    fontWeight: 'bold',
    color: Colors.fadedBlue
  },
  headerValue: {
    width: '100%',
    marginTop: 5,
    fontSize: 16,
    color: Colors.verLightBlack,
    marginBottom: 15,
    fontWeight: '500'
  },
  headerSku: {
    flex: 1,
    alignItems: 'flex-start'
  },
  headerUnit: {
    flex: 1,
    alignItems: 'center'
  },
  headerPackSize: {
    flex: 1,
    alignItems: 'flex-end',
    textAlign: 'right'
  },
  centerText: {
    textAlign: 'center'
  },
  rightText: {
    textAlign: 'right'
  },
  tabView: {
    backgroundColor: '#fff',
    flex: 1
  },
  loading: {
    paddingTop: 50,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.white,
    flex: 1
  },
  categoriesView: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'flex-start',
    flexWrap: 'wrap',
    width: '100%',
    marginTop: 5,
    fontWeight: '500'
  },
  categoryChip: {
    marginTop: 5,
    marginBottom: 5,
    marginRight: 10,
    borderColor: Colors.primary,
    borderWidth: 1
  },
  categoryText: {
    fontSize: 16,
    color: Colors.primary
  },
  addCategoryChip: {
    marginTop: 5,
    marginBottom: 5,
    marginRight: 10,
    borderColor: Colors.primary,
    borderWidth: 1,
    backgroundColor: Colors.primary
  },
  addCategoryText: {
    fontSize: 16,
    color: Colors.white
  },
  footerContainer: {
    padding: 15,
    paddingBottom: 35
  },
  footerItem: {
    textAlign: 'right',
    width: '100%',
    fontSize: 16,
    color: Colors.gray,
    paddingBottom: 8,
  },
  chart: {
    marginTop: 25,
    marginBottom: 25,
    marginRight: 10,
    marginLeft: 0,
    backgroundColor: '#fff',
    height: 300
  },
  chartHeight: 700,
  chartDot: {
    r: '3',
    strokeWidth: '1',
    stroke: Colors.white
  },
  more_vertical: {
    height: 15,
    width: 10,
    marginLeft: 10,
    marginRight: 20,
    alignItems: 'center'
  },
  modal: {
    paddingTop: 20,
    paddingBottom: 20,
    paddingLeft: 10,
    paddingRight: 10,
    backgroundColor: Colors.white,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalHeading: {
    fontSize: 16,
    color: Colors.gray,
    marginTop: 1,
    marginBottom: 1
  },
  modalValue: {
    fontSize: 14,
    color: Colors.gray,
    marginTop: 1,
    marginBottom: 1
  },
  modalButton: {
    marginTop: 25,
    alignItems: 'flex-end'
  },
  modalButtonText: {
    color: Colors.primary,
    fontWeight: 'bold',
    width: '100%',
    textAlign: 'right'
  },
  headerVendorName: {
    flexDirection: 'row'
  },
  headerLeft: {
    flex: 1
  },
  headerRight: {
    flex: 0.2,
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
    flexDirection: 'row'
  },
  missingValue: {
    width: '100%',
    marginTop: 5,
    fontSize: 16,
    color: Colors.missing,
    marginBottom: 15,
    fontWeight: 'normal',
    fontStyle: 'italic'
  },
  starButton: {
    marginBottom: 0,
  },
  starIcon: {
    height: 20
  }
};
