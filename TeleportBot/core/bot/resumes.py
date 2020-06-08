from telegram import Update, ParseMode
from telegram.ext import Filters, ConversationHandler, CallbackQueryHandler, MessageHandler
from core.resources import strings, keyboards
from .utils import Navigation
from core.services import categories


TITLE, DESCRIPTION, CONTACTS, REGION, CITY, CATEGORIES = range(6)


def to_parent_categories(query, context):
    parent_categories = categories.get_parent_categories()
    language = context.user_data['language']
    message = strings.get_string('resumes.create.categories', language)
    keyboard = keyboards.get_parent_categories_keyboard(parent_categories, language)
    query.answer()
    query.edit_message_text(message, reply_markup=keyboard)
    return CATEGORIES


def create(update, context):
    query = update.callback_query
    context.user_data['resume'] = {}
    language = context.user_data['language']
    query.answer(text=strings.get_string('resumes.menu_has_gone', language), show_alert=True)
    message = strings.get_string('resumes.create.title', language)
    keyboard = keyboards.get_keyboard('go_back', language)
    context.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
    context.bot.send_message(chat_id=query.from_user.id, text=message, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    return TITLE


def resume_title(update, context):
    language = context.user_data['language']
    if strings.get_string('go_back', language) in update.message.text:
        Navigation.to_main_menu(update, language)
        return ConversationHandler.END
    context.user_data['resume']['title'] = update.message.text
    message = strings.get_string('resumes.create.description', language)
    update.message.reply_text(message, parse_mode=ParseMode.HTML)
    return DESCRIPTION


def resume_description(update, context):
    language = context.user_data['language']
    if strings.get_string('go_back', language) in update.message.text:
        message = strings.get_string('resumes.create.title', language)
        update.message.reply_text(message)
        return TITLE
    context.user_data['resume']['description'] = update.message.text
    message = strings.get_string('resumes.create.contacts', language)
    update.message.reply_text(message, parse_mode=ParseMode.HTML)
    return CONTACTS


def resume_contacts(update, context):
    language = context.user_data['language']
    if strings.get_string('go_back', language) in update.message.text:
        message = strings.get_string('resumes.create.description', language)
        update.message.reply_text(message)
        return DESCRIPTION
    context.user_data['resume']['contacts'] = update.message.text
    message = strings.get_string('location.regions', language)
    keyboard = keyboards.get_keyboard('location.regions', language)
    update.message.reply_text(message, reply_markup=keyboard)
    return REGION


def resume_region(update, context):
    language = context.user_data['language']

    if update.callback_query:
        query = update.callback_query
        region = query.data.split(':')[1]
        if region == 'all':
            context.user_data['resume']['location'] = region
            return to_parent_categories(query, context)
        region_name = strings.get_string('location.regions.' + region, language)
        context.user_data['resume']['location'] = {}
        context.user_data['resume']['location']['region'] = region
        keyboard = keyboards.get_cities_from_region(region, language)
        message = strings.get_string('location.select.city', language).format(region_name)
        query.edit_message_text(message, reply_markup=keyboard)
        return CITY


def resume_city(update, context):
    language = context.user_data['language']
    query = update.callback_query
    city = query.data.split(':')[1]
    if city == 'back':
        message = strings.get_string('location.regions', language)
        keyboard = keyboards.get_keyboard('location.regions', language)
        query.answer()
        query.edit_message_text(message, keyboard)
        return REGION
    region = context.user_data['resume']['location']['region']
    city_name = strings.get_city_from_region(region, city, language)
    region_name = strings.get_string('location.regions.' + region, language)
    full_name = region_name + ', ' + city_name
    context.user_data['resume']['location']['full_name'] = full_name
    query.answer(text=full_name)
    return to_parent_categories(query, context)


def resume_categories(update, context):
    language = context.user_data['language']
    query = update.callback_query
    category_id = query.data.split(':')[1]
    category = categories.get_category(category_id)
    children_categories = category.get('categories')
    if 'categories' not in context.user_data['resume']:
        context.user_data['resume']['categories'] = []
    if children_categories:
        keyboard = keyboards.get_categories_keyboard(children_categories, language,
                                                     context.user_data['resume']['categories'])
        message = strings.get_category_description(category, language)
        query.edit_message_text(message, reply_markup=keyboard)
        return CATEGORIES
    else:
        if any(d['id'] == category['id'] for d in context.user_data['resume']['categories']):
            added = False
            context.user_data['resume']['categories'][:] = [c for c in context.user_data['resume']['categories'] if c.get('id') != category.get('id')]
        else:
            added = True
            context.user_data['resume']['categories'].append(category)
        category_siblings = categories.get_siblings(category_id)
        keyboard = keyboards.get_categories_keyboard(category_siblings, language,
                                                     context.user_data['resume']['categories'])
        message = strings.from_categories(category, context.user_data['resume']['categories'], added, language)
        answer_message = strings.from_categories_message(category, context.user_data['resume']['categories'], added, language)
        query.answer(text=answer_message)
        query.edit_message_text(message, reply_markup=keyboard)
        return CATEGORIES


resume_create_handler = CallbackQueryHandler(create, pattern='my_resumes:create')
create_resume_conversation = ConversationHandler(
    entry_points=[resume_create_handler],
    states={
        TITLE: [MessageHandler(Filters.text, resume_title)],
        DESCRIPTION: [MessageHandler(Filters.text, resume_description)],
        CONTACTS: [MessageHandler(Filters.text, resume_contacts)],
        REGION: [CallbackQueryHandler(resume_region)],
        CITY: [CallbackQueryHandler(resume_city)],
        CATEGORIES: [CallbackQueryHandler(resume_categories)]
    },
    fallbacks=[MessageHandler(Filters.text, '')]
)